def judicial_decisions(request):
    from django.core.cache import cache
    from django.core.paginator import Paginator
    from django.http import JsonResponse
    from django.db.models import Q
    import time
    
    # AJAX isteği mi kontrol et
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    query = request.GET.get('q', '').strip()
    page_number = request.GET.get('page', 1)
    
    # Initialize variables
    decisions = []
    court_type_counts = {}
    total_results = 0
    search_time = 0
    
    # Arama varsa
    if query:
        start_time = time.time()
        
        # Basit Django ORM sorgusu
        words = query.split()[:3]  # Max 3 kelime
        q_objects = Q()
        for word in words:
            if word.strip():
                q_objects &= Q(karar_ozeti__icontains=word.strip())
        
        # Veritabanından al
        if q_objects:
            results_query = JudicialDecision.objects.filter(q_objects).select_related()
            results_query = results_query.order_by('-karar_tarihi')
            
            # Toplam sayı
            total_results = results_query.count()
            
            # Sayfalama
            paginator = Paginator(results_query, 20)
            page_obj = paginator.get_page(page_number)
            decisions = list(page_obj)
        else:
            total_results = 0
            paginator = Paginator([], 20)
            page_obj = paginator.get_page(page_number)
            decisions = []
        
        search_time = round((time.time() - start_time) * 1000, 2)
        
        # AJAX response
        if is_ajax:
            return JsonResponse({
                'results': [{
                    'id': d.id,
                    'karar_turu': d.karar_turu,
                    'karar_veren_mahkeme': d.karar_veren_mahkeme,
                    'esas_numarasi': d.esas_numarasi,
                    'karar_numarasi': d.karar_numarasi,
                    'karar_tarihi': d.karar_tarihi.strftime('%Y-%m-%d') if d.karar_tarihi else '',
                    'karar_ozeti': d.karar_ozeti[:200] + '...' if d.karar_ozeti and len(d.karar_ozeti) > 200 else d.karar_ozeti,
                    'relevance_score': 1.0
                } for d in decisions],
                'pagination': {
                    'current_page': page_obj.number,
                    'total_pages': page_obj.paginator.num_pages,
                    'has_previous': page_obj.has_previous(),
                    'has_next': page_obj.has_next(),
                    'total_results': total_results
                },
                'court_type_counts': court_type_counts,
                'search_time': search_time,
                'total_decisions': total_results
            })
        
    else:
        # Arama yoksa boş sonuç
        paginator = Paginator([], 20)
        page_obj = paginator.get_page(page_number)
        search_time = 0

    context = {
        'query': query,
        'newest_decisions': decisions,
        'page_obj': page_obj,
        'decisions': decisions,
        'court_type_counts': court_type_counts,
        'total_decisions': total_results,
        'search_time': search_time,
        'has_filters': bool(query),
    }
    return render(request, 'core/judicial_decisions.html', context)
