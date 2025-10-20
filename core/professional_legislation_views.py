# Profesyonel mevzuat views - views.py'e eklenecek

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count
from .models import ProfessionalLegislation, LegislationArticle, LegislationType, LegislationCategory

def professional_legislation_home(request):
    """Profesyonel mevzuat ana sayfası"""
    
    # İstatistikler
    total_legislation = ProfessionalLegislation.objects.filter(status='active').count()
    total_articles = LegislationArticle.objects.filter(is_active=True).count()
    
    # Popüler kategoriler
    popular_categories = LegislationCategory.objects.annotate(
        legislation_count=Count('professionallegislation')
    ).filter(legislation_count__gt=0).order_by('-legislation_count')[:6]
    
    # Son eklenen mevzuatlar
    recent_legislation = ProfessionalLegislation.objects.filter(
        status='active'
    ).order_by('-created_at')[:5]
    
    # Mevzuat türleri
    legislation_types = LegislationType.objects.filter(
        is_active=True
    ).annotate(
        legislation_count=Count('professionallegislation')
    ).order_by('hierarchy_level')
    
    context = {
        'total_legislation': total_legislation,
        'total_articles': total_articles,
        'popular_categories': popular_categories,
        'recent_legislation': recent_legislation,
        'legislation_types': legislation_types,
    }
    
    return render(request, 'core/professional_legislation_home.html', context)

def professional_legislation_detail(request, slug):
    """Profesyonel mevzuat detay sayfası"""
    
    legislation = get_object_or_404(
        ProfessionalLegislation.objects.select_related('legislation_type', 'category'),
        slug=slug,
        status='active'
    )
    
    # Görüntülenme sayısını artır
    legislation.view_count += 1
    legislation.save(update_fields=['view_count'])
    
    # Maddeler (aktif olanlar)
    articles = legislation.articles.filter(is_active=True).order_by('order', 'article_number')
    
    # Sayfalama
    paginator = Paginator(articles, 20)  # Her sayfada 20 madde
    page_number = request.GET.get('page')
    page_articles = paginator.get_page(page_number)
    
    # İlgili mevzuatlar
    related_legislation = legislation.related_legislations.filter(
        status='active'
    )[:5]
    
    # Aynı kategorideki diğer mevzuatlar
    if legislation.category:
        similar_legislation = ProfessionalLegislation.objects.filter(
            category=legislation.category,
            status='active'
        ).exclude(id=legislation.id)[:3]
    else:
        similar_legislation = []
    
    context = {
        'legislation': legislation,
        'articles': page_articles,
        'related_legislation': related_legislation,
        'similar_legislation': similar_legislation,
    }
    
    return render(request, 'core/professional_legislation_detail.html', context)

def professional_legislation_list(request):
    """Profesyonel mevzuat listesi"""
    
    # Filtreleme parametreleri
    category_filter = request.GET.get('category')
    type_filter = request.GET.get('type')
    status_filter = request.GET.get('status', 'active')
    search_query = request.GET.get('q')
    
    # Base queryset
    legislation_qs = ProfessionalLegislation.objects.select_related(
        'legislation_type', 'category'
    ).filter(status=status_filter)
    
    # Filtreleme
    if category_filter:
        legislation_qs = legislation_qs.filter(category__code=category_filter)
    
    if type_filter:
        legislation_qs = legislation_qs.filter(legislation_type__code=type_filter)
    
    if search_query:
        legislation_qs = legislation_qs.filter(
            Q(title__icontains=search_query) |
            Q(number__icontains=search_query) |
            Q(keywords__icontains=search_query)
        )
    
    # Sıralama
    order_by = request.GET.get('order', '-created_at')
    if order_by in ['-created_at', 'title', 'number', '-effective_date']:
        legislation_qs = legislation_qs.order_by(order_by)
    
    # Sayfalama
    paginator = Paginator(legislation_qs, 15)
    page_number = request.GET.get('page')
    page_legislation = paginator.get_page(page_number)
    
    # Filtre seçenekleri
    categories = LegislationCategory.objects.filter(is_active=True).order_by('name')
    types = LegislationType.objects.filter(is_active=True).order_by('hierarchy_level')
    
    context = {
        'legislation_list': page_legislation,
        'categories': categories,
        'types': types,
        'current_category': category_filter,
        'current_type': type_filter,
        'current_status': status_filter,
        'search_query': search_query,
        'current_order': order_by,
    }
    
    return render(request, 'core/professional_legislation_list.html', context)

def professional_article_detail(request, legislation_slug, article_number):
    """Belirli bir madde detayı"""
    
    legislation = get_object_or_404(ProfessionalLegislation, slug=legislation_slug)
    article = get_object_or_404(
        LegislationArticle,
        legislation=legislation,
        article_number=article_number,
        is_active=True
    )
    
    # Görüntülenme sayısını artır
    article.view_count += 1
    article.save(update_fields=['view_count'])
    
    # Önceki ve sonraki maddeler
    prev_article = LegislationArticle.objects.filter(
        legislation=legislation,
        order__lt=article.order,
        is_active=True
    ).order_by('-order').first()
    
    next_article = LegislationArticle.objects.filter(
        legislation=legislation,
        order__gt=article.order,
        is_active=True
    ).order_by('order').first()
    
    context = {
        'legislation': legislation,
        'article': article,
        'prev_article': prev_article,
        'next_article': next_article,
    }
    
    return render(request, 'core/professional_article_detail.html', context)

def increment_legislation_view(request, legislation_id):
    """AJAX ile görüntülenme artırma"""
    if request.method == 'POST':
        try:
            legislation = ProfessionalLegislation.objects.get(id=legislation_id)
            legislation.view_count += 1
            legislation.save(update_fields=['view_count'])
            return JsonResponse({'success': True})
        except ProfessionalLegislation.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Mevzuat bulunamadı'})
    
    return JsonResponse({'success': False, 'error': 'Geçersiz istek'})

def bookmark_article(request):
    """AJAX ile madde kaydetme"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Giriş yapmanız gerekli'})
    
    if request.method == 'POST':
        import json
        data = json.loads(request.body)
        article_id = data.get('article_id')
        
        try:
            article = LegislationArticle.objects.get(id=article_id)
            # Bookmark logic here (create UserBookmark model if needed)
            return JsonResponse({'success': True, 'message': 'Madde kaydedildi'})
        except LegislationArticle.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Madde bulunamadı'})
    
    return JsonResponse({'success': False, 'error': 'Geçersiz istek'})