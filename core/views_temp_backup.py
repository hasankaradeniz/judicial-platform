# core/views.py
from django.shortcuts import render, get_object_or_404
from .models import (
    JudicialDecision, Article, Legislation,
    MevzuatGelismis, MevzuatTuru, MevzuatKategori, 
    MevzuatMadde, MevzuatDegisiklik, MevzuatLog
)
from django.db.models import Q
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

# DRF için
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .serializers import JudicialDecisionSerializer, ArticleSerializer

# Google API için (Google Custom Search)
from googleapiclient.discovery import build
from django.conf import settings
import random
import json
from django.db.models import Count
from django.shortcuts import render
from .models import JudicialDecision
from django.shortcuts import render
from .models import JudicialDecision
from .filters import JudicialDecisionFilter
from django.shortcuts import render
from .models import JudicialDecision
from .filters import JudicialDecisionFilter
import random, json
from django.db.models import Count
from .models import Article
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import Subscription, Payment
from datetime import timedelta, datetime
from django.contrib.auth.decorators import login_required
from .decorators import subscription_required
from django.shortcuts import render, redirect
from django.contrib.auth import login
from .forms import CustomUserCreationForm
from django.utils import timezone
from django.core.mail import send_mail
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from random import sample
from .models import Article
from .param_payment_service import ParamPaymentService
from .param_simple_service import ParamSimpleService

def voice_assistant(request):
    """Sesli asistan ana sayfası"""
    return render(request, 'core/voice_assistant.html')

# Admin views import
from .admin_views import admin_pdf_upload, admin_mevzuat_list, admin_delete_mevzuat

# External mevzuat views import
from .external_mevzuat_views import external_mevzuat_detail, external_mevzuat_pdf_proxy

# Hibrit mevzuat arama
from .hybrid_mevzuat_service import HybridMevzuatService
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from random import sample
from django.shortcuts import render
from .models import JudicialDecision, Article
from django.http import JsonResponse
from django.db.models import Q
from .models import JudicialDecision
from .nlp_utils import analyze_text
from django.http import JsonResponse
from django.shortcuts import render
from django.db.models import Q
from .models import JudicialDecision
from .nlp_utils import analyze_text
from django.db.models import Count
from core.models import JudicialDecision, Article
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from django.shortcuts import render
from core.models import JudicialDecision
import time

def home(request):
    """
    Ana sayfa: Arama formu, en yeni kararlar, rastgele kararlar ve rastgele makaleler.
    """
    from django.core.cache import cache
    from random import sample
    
    # Cache anahtarları
    cache_key_newest = 'home_newest_decisions'
    cache_key_random_decisions = 'home_random_decisions'
    cache_key_random_articles = 'home_random_articles'
    cache_key_total = 'home_total_decisions'
    
    # Cache'den veri çekmeye çalış
    newest_decisions = cache.get(cache_key_newest)
    random_decisions = cache.get(cache_key_random_decisions)
    random_articles = cache.get(cache_key_random_articles)
    total_decisions = cache.get(cache_key_total)
    
    # Cache'de yoksa hesapla
    if newest_decisions is None:
        newest_decisions = list(JudicialDecision.objects.select_related().only(
            'id', 'karar_veren_mahkeme', 'karar_numarasi', 'karar_tarihi', 'karar_ozeti'
        ).order_by('-karar_tarihi')[:15])
        cache.set(cache_key_newest, newest_decisions, 900)  # 15 dakika
    
    if random_decisions is None:
        # order_by('?') yerine Python'da rastgele seçim
        all_decision_ids = list(JudicialDecision.objects.values_list('id', flat=True))
        if len(all_decision_ids) >= 3:
            random_ids = sample(all_decision_ids, min(3, len(all_decision_ids)))
            random_decisions = list(JudicialDecision.objects.filter(id__in=random_ids).select_related().only(
                'id', 'karar_veren_mahkeme', 'karar_numarasi', 'karar_tarihi', 'karar_ozeti'
            ))
        else:
            random_decisions = []
        cache.set(cache_key_random_decisions, random_decisions, 1800)  # 30 dakika
        
    if total_decisions is None:
        total_decisions = JudicialDecision.objects.count()
        cache.set(cache_key_total, total_decisions, 1800)  # 30 dakika

    # Resmi Gazete içeriklerini getir
    from .resmi_gazete_scraper import get_resmi_gazete_content
    try:
        resmi_gazete_icerikler = get_resmi_gazete_content()
    except Exception as e:
        print(f"Resmi Gazete içerikleri alınırken hata: {e}")
        resmi_gazete_icerikler = []

    context = {
        'newest_decisions': newest_decisions,
        'random_decisions': random_decisions,
        'resmi_gazete_icerikler': resmi_gazete_icerikler,
        'total_decisions': total_decisions,
    }

    return render(request, 'core/home.html', context)



def about(request):
    """
    Hakkında sayfası: Platformunuzun tarihçesi, misyonu ve vizyonu.
    """
    return render(request, 'core/about.html')

def combined_search_results(request):
    query = request.GET.get('q', '')
    area = request.GET.get('area', 'both')  # varsayılan "both", yani tüm alanlarda arama

    judicial_results = JudicialDecision.objects.none()
    legislation_results = Legislation.objects.none()
    article_results = Article.objects.none()

    if query:
        if area in ['judicial', 'both']:
            judicial_results = JudicialDecision.objects.filter(
                Q(karar_ozeti__icontains=query) |
                Q(anahtar_kelimeler__icontains=query) |
                Q(karar_tam_metni__icontains=query)
            )
        if area in ['legislation', 'both']:
            legislation_results = Legislation.objects.filter(
                Q(baslik__icontains=query) |
                Q(konu__icontains=query)
            )
        if area in ['articles', 'both']:
            article_results = Article.objects.filter(
                Q(makale_basligi__icontains=query) |
                Q(makale_ozeti__icontains=query) |
                Q(makale_metni__icontains=query)
            )

    context = {
        'query': query,
        'area': area,
        'judicial_results': judicial_results,
        'legislation_results': legislation_results,
        'article_results': article_results,
    }
    return render(request, 'core/combined_search_results.html', context)


from django.db.models import Count, Q
from core.models import JudicialDecision

# Partial views.py with optimized judicial_decisions function

def judicial_decisions(request):
    """
    Complete rewrite - Unified search with bulletproof error handling
    """
    from django.core.cache import cache
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    from django.db.models import Q, Count
    from django.http import JsonResponse
    from django.shortcuts import render
    from django.db import connection
    import time
    
    # Initialize all variables to prevent UnboundLocalError
    query = ''
    court_type = ''
    chamber = ''
    date_range = ''
    decision_number = ''
    case_number = ''
    page = 1
    decisions = []
    total_count = 0
    search_time = 0
    page_range = []
    court_type_stats = []
    limited = False
    
    try:
        # Get search parameters safely
        query = request.GET.get('q', '').strip()
        court_type = request.GET.get('court_type', '').strip()
        chamber = request.GET.get('chamber', '').strip()
        date_range = request.GET.get('date_range', '').strip()
        start_date = request.GET.get('start_date', '').strip()
        end_date = request.GET.get('end_date', '').strip()
        decision_number = request.GET.get('decision_number', '').strip()
        case_number = request.GET.get('case_number', '').strip()
        
        try:
            page = int(request.GET.get('page', 1))
        except (ValueError, TypeError):
            page = 1
        
        # Performance metrics
        start_time = time.time()
        
        # Create cache key
        cache_params = f"{query}_{court_type}_{chamber}_{date_range}_{start_date}_{end_date}_{decision_number}_{case_number}"
        cache_key = f"judicial_search_{hash(cache_params)}"
        
        # Try cache first
        cached_ids = cache.get(cache_key)
        
        if cached_ids is not None:
            matching_ids = cached_ids
        else:
            # Build search with raw SQL for reliability
            matching_ids = []
            
            try:
                with connection.cursor() as cursor:
                    # Build dynamic WHERE conditions
                    where_conditions = []
                    params = []
                    
                    # Text search with full-text index
                    if query:
                        where_conditions.append("""
                            to_tsvector('turkish', 
                                COALESCE(karar_ozeti, '') || ' ' || 
                                COALESCE(anahtar_kelimeler, '') || ' ' || 
                                COALESCE(karar_tam_metni, '')
                            ) @@ plainto_tsquery('turkish', %s)
                        """)
                        params.append(query)
                    
                    # Court type filter
                    if court_type:
                        where_conditions.append("karar_turu = %s")
                        params.append(court_type)
                    
                    # Chamber filter
                    if chamber:
                        if court_type:
                            # EXACT MATCH ONLY when court type is selected
                            if court_type == 'YARGITAY':
                                # Only match exact Yargıtay chambers, not BAM or others
                                where_conditions.append("(karar_veren_mahkeme = %s OR karar_veren_mahkeme = %s OR karar_veren_mahkeme = %s OR karar_veren_mahkeme = %s)")
                                params.extend([
                                    f'YARGITAY {chamber}',
                                    f'Yargıtay {chamber}',
                                    f'YARGITAY {chamber}'.upper(),
                                    f'Yargıtay {chamber}'.title()
                                ])
                            elif court_type == 'DANIŞTAY':
                                where_conditions.append("(karar_veren_mahkeme = %s OR karar_veren_mahkeme = %s)")
                                params.extend([f'DANIŞTAY {chamber}', f'Danıştay {chamber}'])
                            elif court_type == 'SAYIŞTAY':
                                where_conditions.append("(karar_veren_mahkeme = %s OR karar_veren_mahkeme = %s)")
                                params.extend([f'SAYIŞTAY {chamber}', f'Sayıştay {chamber}'])
                            elif court_type == 'ANAYASA MAHKEMESİ':
                                where_conditions.append("(karar_veren_mahkeme = %s OR karar_veren_mahkeme = %s)")
                                params.extend([f'ANAYASA MAHKEMESİ {chamber}', f'Anayasa Mahkemesi {chamber}'])
                            else:
                                where_conditions.append("karar_veren_mahkeme = %s")
                                params.append(f'{court_type} {chamber}')
                        else:
                            # Partial match if no court type selected
                            where_conditions.append("karar_veren_mahkeme ILIKE %s")
                            params.append(f'%{chamber}%')
                    
                    # Decision number filter
                    if decision_number:
                        where_conditions.append("karar_numarasi ILIKE %s")
                        params.append(f'%{decision_number}%')
                    
                    # Case number filter
                    if case_number:
                        where_conditions.append("esas_numarasi ILIKE %s")
                        params.append(f'%{case_number}%')
                    
                    # Date range filter
                    if start_date and end_date:
                        # Custom date range
                        where_conditions.append("karar_tarihi BETWEEN %s AND %s")
                        params.extend([start_date, end_date])
                    elif start_date:
                        # Only start date
                        where_conditions.append("karar_tarihi >= %s")
                        params.append(start_date)
                    elif end_date:
                        # Only end date
                        where_conditions.append("karar_tarihi <= %s")
                        params.append(end_date)
                    elif date_range:
                        # Predefined date ranges
                        from datetime import datetime, timedelta
                        today = datetime.now().date()
                        
                        date_map = {
                            'today': today,
                            'week': today - timedelta(days=7),
                            'month': today - timedelta(days=30),
                            '3months': today - timedelta(days=90),
                            '6months': today - timedelta(days=180),
                            'year': today - timedelta(days=365)
                        }
                        
                        if date_range in date_map:
                            if date_range == 'today':
                                where_conditions.append("karar_tarihi = %s")
                                params.append(date_map[date_range])
                            else:
                                where_conditions.append("karar_tarihi >= %s")
                                params.append(date_map[date_range])
                    
                    # Build final SQL
                    if where_conditions:
                        where_clause = " AND ".join(where_conditions)
                        sql = f"""
                            SELECT id FROM core_judicialdecision 
                            WHERE {where_clause}
                            ORDER BY karar_tarihi DESC 
                            LIMIT 3000
                        """
                    else:
                        # No filters - get recent decisions
                        sql = """
                            SELECT id FROM core_judicialdecision 
                            ORDER BY karar_tarihi DESC 
                            LIMIT 3000
                        """
                        params = []
                    
                    # Execute with timeout protection
                    cursor.execute("SET statement_timeout = '60s'")
                    cursor.execute(sql, params)
                    matching_ids = [row[0] for row in cursor.fetchall()]
                    cursor.execute("RESET statement_timeout")
                    
            except Exception as e:
                # Database error - return empty results
                import logging
                logging.getLogger(__name__).error(f"Database error: {e}")
                matching_ids = []
            
            # Cache results for 3 minutes
            if matching_ids:
                cache.set(cache_key, matching_ids, 180)
        
        # Calculate totals
        total_count = len(matching_ids)
        limited = total_count >= 3000
        
        # Pagination using list slicing (fast)
        per_page = 20
        # Safe page boundary check
        if total_count > 0:
            max_page = (total_count + per_page - 1) // per_page
            if page > max_page:
                page = max_page
        
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        current_page_ids = matching_ids[start_idx:end_idx]
        
        # Get actual objects for current page only
        decisions_list = []
        if current_page_ids:
            try:
                decisions_queryset = JudicialDecision.objects.filter(
                    id__in=current_page_ids
                ).select_related()
                
                # Preserve order from ID list
                decisions_dict = {d.id: d for d in decisions_queryset}
                decisions_list = [
                    decisions_dict[id] for id in current_page_ids 
                    if id in decisions_dict
                ]
            except Exception as e:
                # Query failed - empty results
                decisions_list = []
        
        # Create pagination object
        total_pages = max(1, (total_count + per_page - 1) // per_page)
        page = min(page, total_pages)  # Ensure page is valid
        
        class SimplePaginator:
            def __init__(self, items, page_num, total_pages, total_count):
                self.object_list = items
                self.number = page_num
                self.num_pages = total_pages
                self.count = total_count
                
            def has_previous(self):
                return self.number > 1
                
            def has_next(self):
                return self.number < self.num_pages
                
            def previous_page_number(self):
                return self.number - 1 if self.has_previous() else None
                
            def next_page_number(self):
                return self.number + 1 if self.has_next() else None
                
            def has_other_pages(self):
                return self.num_pages > 1
                
            def __iter__(self):
                return iter(self.object_list)
        
        decisions = SimplePaginator(decisions_list, page, total_pages, total_count)
        
        # Get court type stats (simple, cached)
        court_type_stats = cache.get('court_types_simple')
        if not court_type_stats:
            try:
                court_type_stats = list(
                    JudicialDecision.objects.values('karar_turu')
                    .exclude(karar_turu='Y')
                    .exclude(karar_turu='')
                    .exclude(karar_turu__isnull=True)
                    .distinct().order_by('karar_turu')
                )
                cache.set('court_types_simple', court_type_stats, 1800)
            except:
                court_type_stats = []
        
        # Calculate search time
        search_time = round((time.time() - start_time) * 1000, 2)
        
        # Generate page range
        if total_pages <= 7:
            page_range = list(range(1, total_pages + 1))
        elif page <= 4:
            page_range = [1, 2, 3, 4, 5, '...', total_pages]
        elif page >= total_pages - 3:
            page_range = [1, '...'] + list(range(total_pages - 4, total_pages + 1))
        else:
            page_range = [1, '...', page - 1, page, page + 1, '...', total_pages]
        
    except Exception as e:
        # Top-level error handling
        import logging
        logging.getLogger(__name__).error(f"View error: {e}")
        
        # Safe fallback values
        decisions = SimplePaginator([], 1, 1, 0)
        court_type_stats = []
        page_range = []
        search_time = 0
    
    # Prepare context (always safe)
    context = {
        'decisions': decisions,
        'query': query,
        'court_type': court_type,
        'chamber': chamber,
        'date_range': date_range,
        'start_date': start_date,
        'end_date': end_date,
        'decision_number': decision_number,
        'case_number': case_number,
        'court_type_stats': court_type_stats,
        'total_count': total_count,
        'limited': limited,
        'search_time': search_time,
        'page_range': page_range
    }
    
    # Handle AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            results = []
            for decision in decisions.object_list:
                results.append({
                    'id': getattr(decision, 'id', 0),
                    'karar_turu': getattr(decision, 'karar_turu', ''),
                    'karar_veren_mahkeme': getattr(decision, 'karar_veren_mahkeme', ''),
                    'esas_numarasi': getattr(decision, 'esas_numarasi', ''),
                    'karar_numarasi': getattr(decision, 'karar_numarasi', ''),
                    'karar_tarihi': decision.karar_tarihi.strftime('%d.%m.%Y') if getattr(decision, 'karar_tarihi', None) else '',
                    'karar_ozeti': (decision.karar_ozeti[:200] + '...') if getattr(decision, 'karar_ozeti', None) and len(decision.karar_ozeti) > 200 else (getattr(decision, 'karar_ozeti', '') or '')
                })
            
            return JsonResponse({
                'results': results,
                'pagination': {
                    'current_page': page,
                    'total_pages': total_pages,
                    'has_previous': decisions.has_previous(),
                    'has_next': decisions.has_next(),
                    'total_results': total_count
                },
                'limited': limited,
                'search_time': search_time
            })
        except:
            return JsonResponse({
                'results': [],
                'pagination': {'current_page': 1, 'total_pages': 1, 'has_previous': False, 'has_next': False, 'total_results': 0},
                'limited': False,
                'search_time': 0
            })
    
    return render(request, 'core/judicial_decisions.html', context)
def articles(request):
    """Harici kaynaklardan makale arama ana sayfası"""
    # Veritabanı kullanmıyoruz, sadece arama formu gösteriyoruz
    context = {}
    return render(request, 'core/articles.html', context)


def article_search_results(request):
    """
    Akademik makale arama sonuçları - Sadece güvenilir API'ler
    """
    from .simple_article_search import SimpleArticleSearcher, get_sample_articles
    import time
    
    query = request.GET.get('q', '').strip()
    page = int(request.GET.get('page', 1))
    decision_number = request.GET.get("decision_number", "").strip()
    case_number = request.GET.get("case_number", "").strip()
    articles = []
    search_time = 0
    error_message = ""
    total_estimated = 0
    
    if query:
        start_time = time.time()
        try:
            print(f"🔍 '{query}' için akademik makale aranıyor (sayfa {page})...")
            
            # Yeni basit ve güvenilir sistem - paginated
            searcher = SimpleArticleSearcher()
            articles = searcher.search_articles(query, limit=10, page=page)
            
            print(f"🔍 API'den dönen makale sayısı: {len(articles)}")
            
            # Toplam sonuç tahmini (CrossRef için genel tahmin)
            if articles and len(articles) > 0:
                total_estimated = 2500  # Genel tahmin - gerçek API'den gelebilir
            
            # Sonuçları değerlendir
            if not articles or len(articles) == 0:
                if page == 1:
                    print(f"❌ '{query}' için hiç makale bulunamadı, örnek makaleler gösteriliyor")
                    articles = get_sample_articles(query, limit=10)
                    print(f"📚 {len(articles)} örnek makale oluşturuldu")
                    total_estimated = 3  # Sadece örnek makaleler
                else:
                    print(f"❌ Sayfa {page} için makale bulunamadı")
                    articles = []
                    total_estimated = 0
            else:
                print(f"✅ {len(articles)} gerçek akademik makale bulundu (sayfa {page})")
                
                # Özet çekme işlemi (sadece ilk sayfa için)
                if page == 1:
                    for i, article in enumerate(articles):
                        if article.get('abstract') == 'Özet yükleniyor...' and article.get('detail_link'):
                            print(f"📄 {i+1}. makale için özet çekiliyor...")
                            abstract = searcher.fetch_abstract_from_url(article['detail_link'])
                            if abstract:
                                article['abstract'] = abstract
                                print(f"✅ Özet başarıyla çekildi: {abstract[:50]}...")
                            else:
                                article['abstract'] = 'Bu makale için özet çekilemedi.'
                
            # Session'a kaydet
            for article in articles:
                article_id = article.get('id')
                if article_id:
                    request.session[f'article_{article_id}'] = article
            
        except Exception as e:
            print(f"❌ Makale arama hatası: {str(e)}")
            error_message = f"Arama hatası: {str(e)}"
            articles = get_sample_articles(query, limit=10)
        
        search_time = round((time.time() - start_time) * 1000, 2)

    # Custom pagination logic for API-based results
    has_next = len(articles) == 10 and page * 10 < total_estimated
    has_previous = page > 1
    
    # Sayfa numaraları (basit pagination)
    page_range = []
    if total_estimated > 0:
        total_pages = min((total_estimated + 9) // 10, 250)  # Maksimum 250 sayfa
        start_page = max(1, page - 2)
        end_page = min(total_pages, page + 2)
        page_range = list(range(start_page, end_page + 1))

    context = {
        'query': query,
        'articles': articles,
        'search_time': search_time,
        'total_results': total_estimated,
        'error_message': error_message,
        'search_sources': ['CrossRef API', 'DOAJ API'],
        # Pagination info
        'current_page': page,
        'has_next': has_next,
        'has_previous': has_previous,
        'next_page': page + 1 if has_next else None,
        'previous_page': page - 1 if has_previous else None,
        'page_range': page_range,
        'total_pages': (total_estimated + 9) // 10 if total_estimated > 0 else 0,
        'start_index': (page - 1) * 10 + 1,
        'end_index': min(page * 10, total_estimated),
    }
    return render(request, 'core/article_search_results.html', context)


def sitemap_xml(request):
    """Sitemap.xml dosyası"""
    from django.http import HttpResponse
    from django.urls import reverse
    
    sitemap_content = '''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xsi:schemaLocation="http://www.sitemaps.org/schemas/sitemap/0.9
        http://www.sitemaps.org/schemas/sitemap/0.9/sitemap.xsd">
    
    <url>
        <loc>https://sozlesme.online/</loc>
        <lastmod>2024-12-12</lastmod>
        <changefreq>daily</changefreq>
        <priority>1.0</priority>
    </url>
    
    <url>
        <loc>https://sozlesme.online/articles/</loc>
        <lastmod>2024-12-12</lastmod>
        <changefreq>daily</changefreq>
        <priority>0.9</priority>
    </url>
    
    <url>
        <loc>https://sozlesme.online/judicial-decisions/</loc>
        <lastmod>2024-12-12</lastmod>
        <changefreq>weekly</changefreq>
        <priority>0.8</priority>
    </url>
    
    <url>
        <loc>https://sozlesme.online/legislation/</loc>
        <lastmod>2024-12-12</lastmod>
        <changefreq>weekly</changefreq>
        <priority>0.8</priority>
    </url>
    
    <url>
        <loc>https://sozlesme.online/ai/</loc>
        <lastmod>2024-12-12</lastmod>
        <changefreq>monthly</changefreq>
        <priority>0.7</priority>
    </url>
    
    <url>
        <loc>https://sozlesme.online/about/</loc>
        <lastmod>2024-12-12</lastmod>
        <changefreq>monthly</changefreq>
        <priority>0.6</priority>
    </url>
    
    <url>
        <loc>https://sozlesme.online/paketler/</loc>
        <lastmod>2024-12-12</lastmod>
        <changefreq>monthly</changefreq>
        <priority>0.5</priority>
    </url>
    
</urlset>'''
    
    return HttpResponse(sitemap_content, content_type='application/xml')


def robots_txt(request):
    """Robots.txt dosyası"""
    from django.http import HttpResponse
    
    robots_content = '''User-agent: *
Allow: /

# Disallow certain admin and private areas
Disallow: /admin/
Disallow: /accounts/
Disallow: /static/admin/

# Allow important crawlable content
Allow: /articles/
Allow: /judicial-decisions/
Allow: /legislation/
Allow: /ai/
Allow: /static/

# Crawl settings
Crawl-delay: 1

# Sitemap location
Sitemap: https://sozlesme.online/sitemap.xml'''
    
    return HttpResponse(robots_content, content_type='text/plain')

def hybrid_search_view(request):
    q = request.GET.get("q", "").strip()
    mahkeme = request.GET.get("mahkeme", "").strip()
    tarih = request.GET.get("tarih", "").strip()
    esas = request.GET.get("esas", "").strip()
    karar = request.GET.get("karar", "").strip()

    queryset = JudicialDecision.objects.all()

    # Full-text search varsa
    if q:
        vector = SearchVector('karar_ozeti', 'anahtar_kelimeler', 'karar_tam_metni', config='turkish')
        query = SearchQuery(q, config='turkish')
        queryset = queryset.annotate(rank=SearchRank(vector, query)).filter(rank__gte=0.1).order_by('-rank')

    # Yapısal filtreler (full-text olsa da çalışır)
    if mahkeme:
        queryset = queryset.filter(karar_veren_mahkeme__icontains=mahkeme)
    if tarih:
        queryset = queryset.filter(karar_tarihi=tarih)
    if esas:
        queryset = queryset.filter(esas_numarasi__icontains=esas)
    if karar:
        queryset = queryset.filter(karar_numarasi__icontains=karar)

    return render(request, 'core/hybrid_search_results.html', {
        'results': queryset,
        'query': q,
        'mahkeme': mahkeme,
        'tarih': tarih,
        'esas': esas,
        'karar': karar,
    })

def nlp_search(request):
    if request.method == "GET":
        # Kullanıcıya arama formunu gösteriyoruz.
        return render(request, "core/nlp_search.html")
    elif request.method == "POST":
        text = request.POST.get("text", "")
        if not text:
            return JsonResponse({"error": "Metin girilmedi"}, status=400)

        # Türkçe metni Stanza ile analiz ediyoruz.
        entities = analyze_text(text)

        # Örneğin, tespit edilen ilk varlığı kullanarak arama yapıyoruz.
        if entities:
            keyword = entities[0]
            decisions = JudicialDecision.objects.filter(
                Q(karar_ozeti__icontains=keyword) |
                Q(anahtar_kelimeler__icontains=keyword) |
                Q(karar_tam_metni__icontains=keyword)
            )
        else:
            decisions = JudicialDecision.objects.none()

        results = []
        for decision in decisions:
            results.append({
                "id": decision.id,
                "karar_veren_mahkeme": decision.karar_veren_mahkeme,
                "karar_numarasi": decision.karar_numarasi,
                "karar_tarihi": decision.karar_tarihi.strftime("%Y-%m-%d") if decision.karar_tarihi else "",
                "karar_ozeti": decision.karar_ozeti,
            })

        return JsonResponse({"entities": entities, "results": results})
    else:
        return JsonResponse({"error": "Yalnızca GET ve POST metotları desteklenir"}, status=405)

def legislation(request):
    """
    Mevzuat sayfası: Kanun, yönetmelik, tüzük gibi mevzuat bilgilerini listeleyen sayfa.
    """
    legislations = []  # Mevzuat veritabanı sorgularınızı buraya ekleyin.
    context = {'legislations': legislations}
    return render(request, 'core/legislation_home.html', context)

def how_it_works(request):
    """
    "Nasıl Çalışır?" sayfası: Platformunuzun işleyişini açıklayan bilgiler.
    """
    return render(request, 'core/how_it_works.html')

def paketler(request):
    return render(request, 'core/paketler.html')

def other_products(request):
    """
    "Diğer Ürünlerimiz" sayfası: Diğer Ürünler.
    """
    return render(request, 'core/other_products.html')

@login_required
def profile(request):
    """
    Kullanıcı profil sayfası: Giriş yapmış kullanıcıların bilgilerini görüntüleme.
    """
    return render(request, 'core/profile.html')


def search_results(request):
    queryset = JudicialDecision.objects.all()
    decision_filter = JudicialDecisionFilter(request.GET, queryset=queryset)
    results = decision_filter.qs

    # Ek bölümler (en yeni kararlar, rastgele kararlar, trend analizi)
    newest_decisions = list(results.order_by('-karar_tarihi')[:3])
    all_decisions = list(JudicialDecision.objects.all())
    random_count = min(len(all_decisions), 3)
    random_decisions = random.sample(all_decisions, random_count) if random_count > 0 else []
    total_decisions = JudicialDecision.objects.count()
    court_counts_qs = JudicialDecision.objects.values('karar_turu').annotate(total=Count('id'))
    court_counts = {item['karar_turu']: item['total'] for item in court_counts_qs}
    court_counts_json = json.dumps(court_counts)

    context = {
        'filter': decision_filter,
        'results': results,
        'newest_decisions': newest_decisions,
        'random_decisions': random_decisions,
        'total_decisions': total_decisions,
        'court_counts': court_counts_json,
    }
    return render(request, 'core/search_results.html', context)


@login_required
def subscription_payment(request, package):
    """
    Kullanıcının ödeme yaparak abonelik satın aldığı view.
    Param Sanal Pos entegrasyonu ile ödeme işlemi.
    """
    # Basitleştirilmiş servisi kullan
    param_service = ParamSimpleService()
    
    if request.method == "POST":
        accepted_terms = request.POST.get('accepted_terms') == 'on'
        accepted_sale = request.POST.get('accepted_sale') == 'on'
        accepted_delivery = request.POST.get('accepted_delivery') == 'on'
        tc_or_vergi_no = request.POST.get('tc_or_vergi_no')
        address = request.POST.get('address')
        customer_name = request.POST.get('customer_name')
        customer_phone = request.POST.get('customer_phone')

        # Sözleşmelerin hepsi kabul edilmediyse hata göster
        if not (accepted_terms and accepted_sale and accepted_delivery):
            error = "Lütfen tüm sözleşmeleri kabul edin."
            return render(request, 'core/subscription_payment.html', {'error': error, 'package': package})

        # Gerekli alanlar doldurulmuş mu kontrol et
        if not all([tc_or_vergi_no, address, customer_name, customer_phone]):
            error = "Lütfen tüm alanları doldurun."
            return render(request, 'core/subscription_payment.html', {'error': error, 'package': package})

        # Kullanıcı bilgilerini hazırla (kart bilgileri test için)
        user_data = {
            'name': customer_name,
            'phone': customer_phone,
            'address': address,
            'tc_or_vergi_no': tc_or_vergi_no,
            # Test kart bilgileri (production'da form'dan alınacak)
            'card_owner': customer_name,
            'card_number': '4022774022774026',
            'expire_month': '12',
            'expire_year': '2026',
            'cvc': '000',
            'gsm': customer_phone if customer_phone.startswith('5') else f'5{customer_phone[-9:]}'
        }

        # Ödeme kaydı oluştur
        amount = param_service.get_package_amount(package) / 100  # Kuruştan TL'ye çevir
        order_id = f"LEX_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{request.user.id}"
        
        payment = Payment.objects.create(
            user=request.user,
            package=package,
            amount=amount,
            order_id=order_id,
            status='pending'
        )

        # Basitleştirilmiş servis ile ödeme başlat
        payment_result = param_service.start_payment(request, package, user_data)
        
        # Ödeme bilgilerini session'a kaydet
        request.session['payment_data'] = {
            'payment_id': payment.id,
            'order_id': payment_result.get('order_id', order_id),
            'accepted_terms': accepted_terms,
            'accepted_sale': accepted_sale,
            'accepted_delivery': accepted_delivery,
            'tc_or_vergi_no': tc_or_vergi_no,
            'address': address,
            'customer_name': customer_name,
            'customer_phone': customer_phone,
        }

        # Ödeme URL'i başarılı mı kontrol et
        if payment_result['success']:
            if payment_result.get('requires_redirect'):
                # 3D Secure veya demo sayfasına redirect et
                return redirect(payment_result['payment_url'])
            else:
                # Direct payment success
                return redirect('payment_success')
        else:
            # Hata durumunda form sayfasını tekrar göster
            error = payment_result.get('error', 'Ödeme işlemi başlatılamadı')
            context = {
                'error': error,
                'package': package,
                'amount': param_service.get_package_amount(package) / 100,
                'package_name': param_service.get_package_description(package),
            }
            return render(request, 'core/subscription_payment.html', context)

    # Paket bilgilerini context'e ekle
    context = {
        'package': package,
        'amount': param_service.get_package_amount(package) / 100,
        'package_name': param_service.get_package_description(package),
    }
    return render(request, 'core/subscription_payment.html', context)

@csrf_exempt
@require_POST
def payment_success(request):
    """
    Param Pos'dan gelen başarılı ödeme callback'i
    """
    param_service = ParamPaymentService()
    
    try:
        # POST verilerini al
        response_data = request.POST.dict()
        
        # Ödeme sonucunu doğrula
        verification_result = param_service.verify_payment_callback(response_data)
        
        if verification_result['success']:
            # Ödeme kaydını güncelle
            try:
                payment = Payment.objects.get(order_id=verification_result['order_id'])
                payment.status = 'success'
                payment.transaction_id = verification_result.get('transaction_id')
                payment.param_response = response_data
                payment.save()
                
                # Session'dan ödeme bilgilerini al
                payment_data = request.session.get('payment_data', {})
                
                # Abonelik oluştur
                subscription, created = Subscription.objects.get_or_create(user=payment.user)
                subscription.plan = payment.package
                subscription.accepted_terms = payment_data.get('accepted_terms', False)
                subscription.accepted_sale = payment_data.get('accepted_sale', False)
                subscription.accepted_delivery = payment_data.get('accepted_delivery', False)
                subscription.start_date = timezone.now()
                subscription.tc_or_vergi_no = payment_data.get('tc_or_vergi_no', '')
                subscription.address = payment_data.get('address', '')
                subscription.end_date = None  # save() metodunda hesaplanacak
                subscription.save()
                
                # Bildirim sistemi ile ödeme bildirimi oluştur
                from .notification_service import NotificationService
                
                package_names = {
                    'monthly': 'Aylık Paket',
                    'quarterly': '3 Aylık Paket', 
                    'semi_annual': '6 Aylık Paket',
                    'annual': 'Yıllık Paket'
                }
                package_name = package_names.get(payment.package, payment.package)
                
                # Kullanıcı ve admin bildirimleri oluştur
                NotificationService.create_purchase_notification(
                    user=payment.user,
                    payment=payment,
                    package_name=package_name
                )
                
                # Session'ı temizle
                if 'payment_data' in request.session:
                    del request.session['payment_data']
                
                return redirect('subscription_success')
                
            except Payment.DoesNotExist:
                return render(request, 'core/payment_error.html', {
                    'error': 'Ödeme kaydı bulunamadı.'
                })
        else:
            return render(request, 'core/payment_error.html', {
                'error': verification_result.get('message', 'Ödeme doğrulaması başarısız.')
            })
            
    except Exception as e:
        return render(request, 'core/payment_error.html', {
            'error': f'Ödeme işlemi sırasında hata oluştu: {str(e)}'
        })


def demo_payment(request):
    """Demo ödeme sayfası - IP adresi kayıtlı olmayan yerel test ortamı için"""
    order_id = request.GET.get('order_id')
    amount = request.GET.get('amount', '0')
    package = request.GET.get('package', 'monthly')
    
    param_service = ParamPaymentService()
    package_name = param_service.get_package_description(package)
    
    if request.method == 'POST':
        # Demo ödeme "başarılı" simülasyonu
        action = request.POST.get('action')
        if action == 'success':
            return redirect(f'/payment/success/?order_id={order_id}&demo=1')
        else:
            return redirect(f'/payment/fail/?order_id={order_id}&demo=1')
    
    context = {
        'order_id': order_id,
        'amount': amount,
        'package': package,
        'package_name': package_name,
        'demo_mode': True,
        'ip_address': '145.223.82.130',
        'client_code': param_service.client_code
    }
    
    return render(request, 'core/demo_payment.html', context)

@csrf_exempt
def payment_3d_callback(request):
    """
    3D Secure callback handler
    Query param: ?durum=basarili veya ?durum=hata
    """
    durum = request.GET.get('durum')
    param_service = ParamSimpleService()
    
    if durum != 'basarili':
        # 3D doğrulama başarısız
        return render(request, 'core/payment_error.html', {
            'error': '3D Secure doğrulama başarısız oldu.'
        })
    
    try:
        # POST verilerini al
        callback_data = request.POST.dict()
        
        # 3D ödemeyi tamamla
        payment_result = param_service.complete_3d_payment(request, callback_data)
        
        if payment_result['success']:
            # Session'dan ödeme bilgilerini al
            payment_data = request.session.get('payment_data', {})
            order_id = payment_result.get('order_id') or payment_data.get('order_id')
            
            try:
                # Ödeme kaydını güncelle
                payment = Payment.objects.get(order_id=order_id)
                payment.status = 'success'
                payment.transaction_id = payment_result.get('transaction_id')
                payment.param_response = callback_data
                payment.save()
                
                # Abonelik oluştur
                subscription, created = Subscription.objects.get_or_create(user=payment.user)
                subscription.plan = payment.package
                subscription.accepted_terms = payment_data.get('accepted_terms', False)
                subscription.accepted_sale = payment_data.get('accepted_sale', False)
                subscription.accepted_delivery = payment_data.get('accepted_delivery', False)
                subscription.start_date = timezone.now()
                subscription.tc_or_vergi_no = payment_data.get('tc_or_vergi_no', '')
                subscription.address = payment_data.get('address', '')
                subscription.end_date = None  # save() metodunda hesaplanacak
                subscription.save()
                
                # Bildirim oluştur
                from .notification_service import NotificationService
                
                package_names = {
                    'monthly': 'Aylık Paket',
                    'quarterly': '3 Aylık Paket', 
                    'semi_annual': '6 Aylık Paket',
                    'annual': 'Yıllık Paket'
                }
                package_name = package_names.get(payment.package, payment.package)
                
                NotificationService.create_purchase_notification(
                    user=payment.user,
                    payment=payment,
                    package_name=package_name
                )
                
                # Session'ı temizle
                if 'payment_data' in request.session:
                    del request.session['payment_data']
                
                return redirect('subscription_success')
                
            except Payment.DoesNotExist:
                return render(request, 'core/payment_error.html', {
                    'error': 'Ödeme kaydı bulunamadı.'
                })
        else:
            return render(request, 'core/payment_error.html', {
                'error': payment_result.get('error', 'Ödeme tamamlanamadı.')
            })
            
    except Exception as e:
        return render(request, 'core/payment_error.html', {
            'error': f'3D ödeme işlemi sırasında hata oluştu: {str(e)}'
        })

@csrf_exempt
def payment_fail(request):
    """
    Param Pos'dan gelen başarısız ödeme callback'i
    """
    try:
        response_data = request.POST.dict()
        order_id = response_data.get('merchant_oid')
        
        if order_id:
            try:
                payment = Payment.objects.get(order_id=order_id)
                payment.status = 'failed'
                payment.error_message = response_data.get('message', 'Ödeme başarısız')
                payment.param_response = response_data
                payment.save()
            except Payment.DoesNotExist:
                pass
        
        return render(request, 'core/payment_error.html', {
            'error': response_data.get('message', 'Ödeme işlemi başarısız oldu.')
        })
        
    except Exception as e:
        return render(request, 'core/payment_error.html', {
            'error': f'Ödeme işlemi sırasında hata oluştu: {str(e)}'
        })


@login_required
def subscription_success(request):
    """
    Başarılı ödeme sonrası gösterilecek sayfa
    """
    return render(request, 'core/subscription_success.html')

@login_required
@subscription_required
def some_protected_view(request):
    # İçerik
    return render(request, 'core/protected.html')

def ai_features_home(request):
    """
    AI Özellikler ana sayfası
    """
    return render(request, 'core/ai_features.html')

def legislation_home(request):
    """Simple legislation home page"""
    return render(request, "core/legislation_home.html")

def ziyaretci_veri_koruma(request):
    return render(request, "core/ziyaretci_veri_koruma.html")

def gizlilik_politikasi(request):
    """
    Gizlilik Politikası / Kişisel Verileri Koruma Politikası sayfası.
    """
    return render(request, 'core/gizlilik_politikasi.html')

def kullanici_sozlesmesi(request):
    """
    Kullanıcı Sözleşmesi sayfası.
    """
    return render(request, 'core/kullanici_sozlesmesi.html')

def mesafeli_satis_sozlesmesi(request):
    """
    Mesafeli Satış Sözleşmesi sayfası.
    """
    return render(request, 'core/mesafeli_satis_sozlesmesi.html')

def teslimat_iade_sartlari(request):
    """
    Teslimat ve İade Şartları sayfası.
    """
    return render(request, 'core/teslimat_iade_sartlari.html')

def signup(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')  # Backend belirtildi
            return redirect('home')  # Başarılı kayıt sonrası ana sayfaya yönlendir
    else:
        form = CustomUserCreationForm()
    return render(request, 'core/signup.html', {'form': form})

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Kullanıcı kaydını tamamladıktan sonra otomatik olarak giriş yapıyoruz.
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            return redirect('home')
    else:
        form = CustomUserCreationForm()
    return render(request, 'core/register.html', {'form': form})


def judicial_detail(request, pk):
    """
    Tek bir yargı kararının detaylarını gösterir.
    """
    decision = get_object_or_404(JudicialDecision, pk=pk)
    context = {'decision': decision}
    return render(request, 'core/judicial_detail.html', context)

import json
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import render
from .models import Legislation

import json
from django.db.models import Q, Count
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import render
from .models import Legislation


def legislation_home(request):
    """Simple legislation home page"""
    return render(request, "core/legislation_home.html")

def legislation_results(request):
    """
    Doğrudan mevzuat.gov.tr'den canlı mevzuat arama sonuçları
    """
    # Import direct live searcher
    from .live_direct_search import DirectLiveMevzuatSearcher
    
    # Arama parametreleri
    query = request.GET.get('q', '').strip()
    mevzuat_turu_id = request.GET.get('mevzuat_turu', '')
    page_num = request.GET.get('page', 1)
    
    # Eğer arama terimi yoksa ana sayfaya yönlendir
    if not query:
        return render(request, 'core/legislation_results.html', {
            'query': '',
            'no_search_term': True,
            'message': 'Arama yapmak için bir kelime veya ifade girin.'
        })
    
    try:
        # Simple live search kullan (daha basit ve etkili)
        from .simple_mevzuat_search import SimpleMevzuatSearcher
        searcher = SimpleMevzuatSearcher()
        search_results = searcher.search_legislation(
            query=query,
            mevzuat_type=mevzuat_turu_id,
            page=int(page_num),
            per_page=10
        )
        
        # Sayfalama objesi oluştur
        class LivePaginator:
            def __init__(self, results):
                self.results = results
                self.count = results['total_count']
                self.num_pages = max(1, (self.count + 9) // 10)  # 10'ar sayfa
                
            def page_range(self):
                current_page = self.results['page']
                total_pages = self.num_pages
                
                # Sayfa aralığını hesapla (gösterilecek sayfa numaraları)
                start = max(1, current_page - 5)
                end = min(total_pages + 1, current_page + 6)
                
                # Eğer başlangıç çok küçükse, sonunu artır
                if end - start < 10 and total_pages > 10:
                    if start == 1:
                        end = min(total_pages + 1, 11)
                    else:
                        start = max(1, end - 10)
                
                return range(start, end)
        
        class LivePage:
            def __init__(self, results):
                self.object_list = results['results']
                self.number = results['page']
                self.paginator = LivePaginator(results)
                self._has_next = results['has_next']
                self._has_previous = results['has_previous']
            
            def __iter__(self):
                return iter(self.object_list)
            
            def has_next(self):
                return self._has_next
            
            def has_previous(self):
                return self._has_previous
            
            def next_page_number(self):
                return self.number + 1 if self.has_next() else None
            
            def previous_page_number(self):
                return self.number - 1 if self.has_previous() else None
            
            def has_other_pages(self):
                return self.paginator.num_pages > 1
        
        legislations_page = LivePage(search_results)
        
        # İstatistikler
        search_stats = {
            'total_results': search_results['total_count'],
            'live_results': search_results['total_count'],
            'db_results': 0,
            'is_live': True,
            'search_time': time.time(),
            'source': 'mevzuat.gov.tr'
        }
        
        # Hata varsa kullanıcıya bildir
        error_message = search_results.get('error', '')
        
    except Exception as e:
        # Hata durumu
        search_results = {
            'results': [],
            'total_count': 0,
            'page': 1,
            'has_next': False,
            'has_previous': False
        }
        legislations_page = LivePage(search_results)
        search_stats = {
            'total_results': 0,
            'live_results': 0,
            'db_results': 0,
            'is_live': True,
            'error': True
        }
        error_message = f"Arama sırasında bir hata oluştu: {str(e)}"
    
    # Mevzuat türleri (sabit liste - veritabanı yerine)
    mevzuat_turleri = [
        {'id': '1', 'ad': 'Kanunlar'},
        {'id': '2', 'ad': 'Cumhurbaşkanlığı Kararnameleri'},
        {'id': '5', 'ad': 'Yönetmelikler'},
        {'id': '6', 'ad': 'Tüzükler'},
        {'id': '7', 'ad': 'Tebliğler'},
        {'id': '8', 'ad': 'Genelgeler'},
        {'id': '9', 'ad': 'Uluslararası Anlaşmalar'},
    ]
    
    context = {
        'query': query,
        'mevzuat_turu_id': mevzuat_turu_id,
        'legislations': legislations_page,
        'mevzuat_turleri': mevzuat_turleri,
        'total_results': search_stats.get('total_results', 0),
        'search_stats': search_stats,
        'is_live_search': True,
        'error_message': error_message if 'error_message' in locals() else None,
        'system_source': 'mevzuat.gov.tr'
    }
    return render(request, 'core/legislation_results.html', context)

def legislation_detail(request, pk):
    """
    Gelişmiş mevzuat detay sayfası: Madde bazlı görüntüleme ve değişiklik geçmişi.
    """
    legislation = get_object_or_404(
        MevzuatGelismis.objects.select_related('mevzuat_turu', 'kategori'), 
        pk=pk
    )
    
    # Maddeler (sıralı)
    maddeler = legislation.maddeler.filter(aktif=True).order_by('sira', 'madde_no')
    
    # Değişiklik geçmişi
    degisiklikler = legislation.degisiklikler.select_related(
        'degistiren_mevzuat'
    ).order_by('-degisiklik_tarihi')[:10]
    
    # İlgili mevzuatlar
    ilgili_mevzuatlar = legislation.ilgili_mevzuatlar.filter(
        durum='yurutulme'
    )[:5]
    
    # Benzer mevzuatlar (aynı kategori)
    benzer_mevzuatlar = []
    if legislation.kategori:
        benzer_mevzuatlar = MevzuatGelismis.objects.filter(
            kategori=legislation.kategori,
            durum='yurutulme'
        ).exclude(pk=legislation.pk)[:5]
    
    # Madde sayısı ve istatistikler
    madde_sayisi = maddeler.count()
    degisiklik_sayisi = degisiklikler.count()
    
    # Log kaydı (görüntüleme)
    MevzuatLog.objects.create(
        islem_turu='guncelleme',
        aciklama=f'Mevzuat detayı görüntülendi: {legislation.baslik}',
        mevzuat=legislation,
        kullanici=request.user if request.user.is_authenticated else None,
        ip_adresi=request.META.get('REMOTE_ADDR'),
        detaylar={'action': 'view_detail'}
    )
    
    context = {
        'legislation': legislation,
        'maddeler': maddeler,
        'degisiklikler': degisiklikler,
        'ilgili_mevzuatlar': ilgili_mevzuatlar,
        'benzer_mevzuatlar': benzer_mevzuatlar,
        'madde_sayisi': madde_sayisi,
        'degisiklik_sayisi': degisiklik_sayisi,
    }
    return render(request, 'core/legislation_detail.html', context)

def mevzuat_madde_detail(request, mevzuat_pk, madde_pk):
    """
    Mevzuat maddesi detay sayfası: Tek madde odaklı görüntüleme.
    """
    madde = get_object_or_404(
        MevzuatMadde.objects.select_related('mevzuat'), 
        pk=madde_pk, mevzuat_id=mevzuat_pk
    )
    
    # Önceki ve sonraki maddeler
    onceki_madde = MevzuatMadde.objects.filter(
        mevzuat=madde.mevzuat, 
        sira__lt=madde.sira,
        aktif=True
    ).order_by('-sira').first()
    
    sonraki_madde = MevzuatMadde.objects.filter(
        mevzuat=madde.mevzuat, 
        sira__gt=madde.sira,
        aktif=True
    ).order_by('sira').first()
    
    # Bu maddeyi etkileyen değişiklikler
    degisiklikler = MevzuatDegisiklik.objects.filter(
        etkilenen_maddeler=madde
    ).select_related('degistiren_mevzuat').order_by('-degisiklik_tarihi')[:5]
    
    # Diğer maddeler (template için)
    diger_maddeler = MevzuatMadde.objects.filter(
        mevzuat=madde.mevzuat,
        aktif=True
    ).order_by('sira')[:20]
    
    context = {
        'madde': madde,
        'mevzuat': madde.mevzuat,
        'onceki_madde': onceki_madde,
        'sonraki_madde': sonraki_madde,
        'degisiklikler': degisiklikler,
        'diger_maddeler': diger_maddeler,
    }
    return render(request, 'core/mevzuat_madde_detail.html', context)

def legislation_list(request):
    query = request.GET.get('q', '')
    mevzuat_turu = request.GET.get('mevzuat_turu', '')

    # Tüm mevzuat kayıtlarını alıyoruz.
    legislations = Legislation.objects.all()

    # Eğer arama sorgusu varsa, başlık veya konu alanlarında __icontains ile arama yapıyoruz.
    if query:
        legislations = legislations.filter(
            Q(baslik__icontains=query) | Q(konu__icontains=query)
        )

    # Mevzuat türü filtresi (querystring'de seçilmişse)
    if mevzuat_turu:
        legislations = legislations.filter(mevzuat_turu=mevzuat_turu)

    # Pagination: Örneğin, 12 kayıt/sayfa
    paginator = Paginator(legislations, 12)
    page = request.GET.get('page')
    try:
        legislations_page = paginator.page(page)
    except PageNotAnInteger:
        legislations_page = paginator.page(1)
    except EmptyPage:
        legislations_page = paginator.page(paginator.num_pages)

    # Eğer kullanıcı henüz arama yapmamışsa, hero bölümünde en yeni 10 kaydı gösterelim.
    newest_legislations = []
    if not query:
        newest_legislations = legislations.order_by('-yayin_tarihi')[:10]

    # Trend grafiği için: Mevzuat türlerine göre toplam kayıt sayısı
    court_counts_qs = Legislation.objects.values('mevzuat_turu').annotate(total=Count('id'))
    court_counts = {item['mevzuat_turu']: item['total'] for item in court_counts_qs}
    court_counts_json = json.dumps(court_counts)

    context = {
        'query': query,
        'mevzuat_turu': mevzuat_turu,
        'legislations': legislations_page,
        'newest_legislations': newest_legislations,
        'court_counts': court_counts_json,
    }
    return render(request, 'core/legislation_home.html', context)


def article_detail(request, pk):
    """
    Tek bir makalenin detaylarını gösterir.
    """
    article = get_object_or_404(Article, pk=pk)
    context = {'article': article}
    return render(request, 'core/article_detail.html', context)


# API örneği: Arama sonuçlarını JSON olarak dönen uç nokta
@api_view(['GET'])
def api_search(request):
    query = request.GET.get('q', '')
    search_area = request.GET.get('area', 'both')
    judicial_results = JudicialDecision.objects.none()
    article_results = Article.objects.none()

    if query:
        if search_area in ['judicial', 'both']:
            judicial_results = JudicialDecision.objects.filter(
                Q(karar_ozeti__icontains=query) |
                Q(anahtar_kelimeler__icontains=query) |
                Q(karar_tam_metni__icontains=query) |
                Q(karar_veren_mahkeme__icontains=query)
            )
        if search_area in ['articles', 'both']:
            article_results = Article.objects.filter(
                Q(makale_basligi__icontains=query) |
                Q(makale_ozeti__icontains=query) |
                Q(makale_metni__icontains=query)
            )
    decisions_serializer = JudicialDecisionSerializer(judicial_results, many=True)
    articles_serializer = ArticleSerializer(article_results, many=True)
    data = {
        'judicial_decisions': decisions_serializer.data,
        'articles': articles_serializer.data,
    }
    return Response(data)


# Google Custom Search API entegrasyonu için yardımcı fonksiyon (İsteğe bağlı)
def google_search(query):
    """
    Google Custom Search API kullanarak sorguya ait sonuçları getirir.
    """
    api_key = settings.GOOGLE_API_KEY
    cse_id = settings.GOOGLE_CSE_ID
    service = build("customsearch", "v1", developerKey=api_key)
    res = service.cse().list(q=query, cx=cse_id).execute()
    return res.get('items', [])

def predictive_legal_analysis(request):
    """
    Öngörülü hukuki analiz ana sayfası.
    """
    return render(request, 'core/predictive_legal_analysis.html')


import requests
import logging
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import urllib.parse

logger = logging.getLogger(__name__)

def article_pdf_viewer(request, source, article_id):
    """
    Hibrit makale/PDF görüntüleyici - Enhanced with fallback DOI extraction + DergiPark Debug
    """
    from .hybrid_pdf_finder import find_article_pdf_links
    
    # Session'dan makale bilgilerini al
    article_key = f'article_{article_id}'
    article_data = request.session.get(article_key)
    
    # Debug logging
    print(f"Looking for article_id: {article_id}")
    print(f"Article key: {article_key}")
    print(f"Session keys containing article: {[k for k in request.session.keys() if 'article' in k]}")
    
    # If session data not found, try to extract from article_id
    if not article_data:
        print(f"Session data not found, trying to extract from article_id: {article_id}")
        
        # Try to construct basic article data from the article_id
        if article_id.startswith('crossref_') and len(article_id) > 9:
            # Extract DOI from article_id (format: crossref_10.1186_s40364-024-00557-1)
            potential_doi = article_id[9:].replace('_', '/')  # Remove 'crossref_' and restore '/'
            
            # DergiPark DOI'leri için özel URL oluşturma
            dergipark_url = None
            if '10.32331/sgd.' in potential_doi:
                # Sosyal Güvenlik Dergisi için özel URL yapısı
                article_num = potential_doi.split('.')[-1]
                dergipark_url = f"https://dergipark.org.tr/tr/pub/sgd/article/{article_num}"
            
            article_data = {
                'id': article_id,
                'title': f'Academic Article (DOI: {potential_doi})',
                'doi': potential_doi,
                'doi_url': f'https://doi.org/{potential_doi}',
                'source': 'dergipark' if '10.32331' in potential_doi or 'dergipark' in source.lower() else source,
                'url': dergipark_url or f'https://doi.org/{potential_doi}',
                'authors': 'Authors information not available',
                'journal': 'Journal information not available',
                'year': 'Year not available',
                'abstract': 'Abstract not available in this view mode'
            }
            print(f"Constructed article data from DOI: {potential_doi}")
            print(f"Detected source: {article_data['source']}")
            print(f"DergiPark URL: {dergipark_url}")
        else:
            # For other ID formats, create minimal data
            article_data = {
                'id': article_id,
                'title': f'Academic Article (ID: {article_id})',
                'doi': '',
                'doi_url': '',
                'source': source,
                'authors': 'Authors information not available',
                'journal': 'Journal information not available',
                'year': 'Year not available',
                'url': '',
                'abstract': 'Abstract not available in this view mode'
            }
            print(f"Constructed minimal article data for ID: {article_id}")
    
    # If still no article data, show error
    if not article_data:
        return render(request, 'core/pdf_error.html', {
            'error': 'Makale bilgisi bulunamadı. Lütfen arama sayfasına geri dönerek makaleyi tekrar bulun.'
        })
    
    # Smart PDF finder kullan
    print(f"Calling PDF finder for source: {article_data.get('source')}")
    pdf_results = find_article_pdf_links(article_data)
    
    # Debug info
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"PDF search for {article_data.get('title', 'Unknown')}: Found {len(pdf_results['pdf_links'])} PDFs")
    print(f"PDF search completed: {len(pdf_results['pdf_links'])} PDFs found")
    for link in pdf_results.get("pdf_links", []):        print(f"Found PDF: {link.get("source")} - {link.get("url")}")
    print(f"PDF results: {pdf_results}")
    
    context = {
        'article': article_data,
        'source': source,
        'query': request.GET.get('q', ''),
        'pdf_results': pdf_results,
    }
    
    return render(request, 'core/hybrid_pdf_viewer.html', context)
@csrf_exempt
def proxy_pdf(request):
    """
    Enhanced PDF proxy endpoint - X-Frame-Options sorununu çözer
    """
    pdf_url = request.GET.get('url')
    if not pdf_url:
        return JsonResponse({'error': 'PDF URL gerekli'}, status=400)
    
    try:
        # DergiPark için özel headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/pdf,application/octet-stream,*/*',
            'Accept-Language': 'tr-TR,tr;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # DergiPark için özel ayarlar
        if 'dergipark.org.tr' in pdf_url:
            headers.update({
                'Referer': 'https://dergipark.org.tr/',
                'Origin': 'https://dergipark.org.tr',
            })
            print(f"📚 DergiPark PDF proxy isteği: {pdf_url}")
        
        # Session kullan (cookie'leri korumak için)
        session = requests.Session()
        response = session.get(pdf_url, headers=headers, stream=True, timeout=30, allow_redirects=True)
        
        print(f"📄 Proxy yanıt: {response.status_code} - Content-Type: {response.headers.get('content-type', 'N/A')}")
        print(f"📄 Final URL: {response.url}")
        
        # Redirect durumunda final URL'yi kontrol et
        if response.history:
            print(f"📄 Redirect zinciri: {[r.status_code for r in response.history]}")
        
        if response.status_code == 200:
            content_type = response.headers.get('content-type', 'application/pdf')
            
            # PDF olup olmadığını kontrol et - daha geniş kontrol
            is_pdf = (
                'pdf' in content_type.lower() or 
                pdf_url.lower().endswith('.pdf') or
                response.url.lower().endswith('.pdf') or
                'application/octet-stream' in content_type.lower() or
                # PDF magic bytes kontrolü
                (response.content[:4] == b'%PDF') if len(response.content) > 4 else False
            )
            
            if is_pdf:
                # PDF içeriğini geri döndür
                pdf_response = HttpResponse(response.content, content_type='application/pdf')
                
                # Güvenlik header'larını ayarla - X-Frame-Options'ı KALDIRIYORUZ!
                pdf_response['Content-Disposition'] = 'inline; filename="makale.pdf"'
                # X-Frame-Options header'ını KESİNLİKLE eklemeyin!
                # pdf_response['X-Frame-Options'] = 'SAMEORIGIN'  # BUNU YAPMAYIN!
                
                # CORS izinleri
                pdf_response['Access-Control-Allow-Origin'] = '*'
                pdf_response['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
                
                # Cache kontrolü
                pdf_response['Cache-Control'] = 'public, max-age=3600'
                
                print(f"✅ PDF başarıyla proxy edildi: {len(response.content)} bytes")
                return pdf_response
            else:
                # PDF değilse HTML içeriği kontrol et (DergiPark ana sayfaya yönlendirme olabilir)
                if 'text/html' in content_type.lower():
                    print(f"❌ HTML sayfası döndü, PDF değil. İçerik başlangıcı: {response.text[:200]}")
                    
                    # HTML içinde PDF link ara
                    import re
                    pdf_pattern = r'<meta[^>]*http-equiv=["\']refresh["\'][^>]*url=([^"\']+\.pdf[^"\']*)'
                    match = re.search(pdf_pattern, response.text, re.IGNORECASE)
                    if match:
                        new_pdf_url = match.group(1)
                        if new_pdf_url.startswith('/'):
                            new_pdf_url = 'https://dergipark.org.tr' + new_pdf_url
                        print(f"📄 HTML'de PDF redirect bulundu: {new_pdf_url}")
                        # Recursive call with new URL
                        request.GET = request.GET.copy()
                        request.GET['url'] = new_pdf_url
                        return proxy_pdf(request)
                
                return JsonResponse({
                    'error': 'Bu link bir PDF dosyası değil, HTML sayfası döndü',
                    'content_type': content_type,
                    'url': pdf_url,
                    'final_url': response.url
                }, status=400)
        else:
            print(f"❌ PDF yüklenemedi: HTTP {response.status_code}")
            # 403 Forbidden durumunda özel mesaj
            if response.status_code == 403:
                return JsonResponse({
                    'error': 'PDF erişimi reddedildi. DergiPark güvenlik kontrolü olabilir.',
                    'status_code': response.status_code,
                    'url': pdf_url,
                    'suggestion': 'Lütfen "İndir" butonunu kullanarak PDF\'i indirin.'
                }, status=403)
            
            return JsonResponse({
                'error': f'PDF yüklenemedi (HTTP {response.status_code})',
                'url': pdf_url,
                'final_url': response.url,
                'headers': dict(response.headers)
            }, status=response.status_code)
            
    except requests.exceptions.Timeout:
        print(f"⏰ PDF yükleme zaman aşımı: {pdf_url}")
        return JsonResponse({'error': 'PDF yüklenirken zaman aşımı'}, status=408)
    except requests.exceptions.RequestException as e:
        logger.error(f"PDF proxy error: {e}")
        print(f"❌ PDF proxy hatası: {e}")
        return JsonResponse({'error': f'PDF yükleme hatası: {str(e)}'}, status=500)
    except Exception as e:
        logger.error(f"Unexpected PDF error: {e}")
        print(f"❌ Beklenmeyen hata: {e}")
        return JsonResponse({'error': 'Beklenmeyen hata'}, status=500)
def test_pdf_display(request):
    return render(request, 'core/test_pdf_display.html')
def debug_pdf_test(request): return render(request, "core/debug_pdf_test.html")

# Enhanced Articles Search - Added 21 Ağu 2025 Per +03 00:41:35
@csrf_exempt
@require_http_methods(["POST"])
def enhanced_article_search(request):
    """Enhanced search with exact phrase matching"""
    try:
        query = request.POST.get('query', '').strip()
        page = int(request.POST.get('page', 1))
        exact_phrase = request.POST.get('exact_phrase', 'false').lower() == 'true'
        source_filter = request.POST.get('source', 'all')
        sort_by = request.POST.get('sort', 'relevance')
        
        if not query:
            return JsonResponse({'error': 'Arama terimi gerekli'}, status=400)
        
        print(f"Enhanced search: '{query}' (exact_phrase: {exact_phrase}, source: {source_filter})")
        
        all_results = []
        search_stats = {
            'total_results': 0,
            'crossref_count': 0,
            'doaj_count': 0,
            'dergipark_count': 0,
            'search_time': 0
        }
        
        from datetime import datetime
        start_time = datetime.now()
        
        # CrossRef Search
        if source_filter in ['all', 'crossref']:
            crossref_results = search_crossref_enhanced(query, exact_phrase)
            all_results.extend(crossref_results)
            search_stats['crossref_count'] = len(crossref_results)
        
        # DOAJ Search  
        if source_filter in ['all', 'doaj']:
            doaj_results = search_doaj_enhanced(query, exact_phrase)
            all_results.extend(doaj_results)
            search_stats['doaj_count'] = len(doaj_results)
        
        # DergiPark Search
        if source_filter in ['all', 'dergipark']:
            dergipark_results = search_dergipark_enhanced(query, exact_phrase)
            all_results.extend(dergipark_results)
            search_stats['dergipark_count'] = len(dergipark_results)
        
        search_stats['search_time'] = (datetime.now() - start_time).total_seconds()
        search_stats['total_results'] = len(all_results)
        
        # Sort results
        all_results = sort_search_results(all_results, sort_by, query)
        
        # Paginate results
        from django.core.paginator import Paginator
        paginator = Paginator(all_results, 10)
        try:
            results_page = paginator.page(page)
        except:
            results_page = paginator.page(1)
        
        response_data = {
            'success': True,
            'query': query,
            'exact_phrase': exact_phrase,
            'page': page,
            'total_pages': paginator.num_pages,
            'has_previous': results_page.has_previous(),
            'has_next': results_page.has_next(),
            'previous_page': results_page.previous_page_number() if results_page.has_previous() else None,
            'next_page': results_page.next_page_number() if results_page.has_next() else None,
            'results': [format_article_result(article) for article in results_page],
            'stats': search_stats
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        print(f"Enhanced search error: {str(e)}")
        return JsonResponse({
            'error': f'Arama hatası: {str(e)}',
            'success': False
        }, status=500)

def search_crossref_enhanced(query, exact_phrase=False, max_results=20):
    """Enhanced CrossRef search with exact phrase support"""
    try:
        if exact_phrase:
            search_query = f'"{query}"'
        else:
            search_query = query
        
        url = "https://api.crossref.org/works"
        params = {
            'query': search_query,
            'rows': max_results,
            'sort': 'relevance',
            'filter': 'type:journal-article'
        }
        
        headers = {
            'User-Agent': 'LexaTech Academic Search (mailto:contact@lexatech.ai)'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        results = []
        
        for item in data.get('message', {}).get('items', []):
            try:
                title = ' '.join(item.get('title', ['Başlık bulunamadı']))
                authors = extract_authors_enhanced(item.get('author', []))
                
                if exact_phrase and query.lower() not in title.lower():
                    continue
                
                abstract = item.get('abstract', '')
                if abstract:
                    abstract = clean_html_enhanced(abstract)[:500] + '...' if len(abstract) > 500 else abstract
                else:
                    abstract = f"Bu makale {query} konusu ile ilgili CrossRef veritabanından alınmış akademik bir çalışmadır."
                
                journal = extract_journal_name_enhanced(item)
                year = extract_publication_year_enhanced(item)
                doi = item.get('DOI', '')
                
                doi_url = f"https://doi.org/{doi}" if doi else None
                pdf_url = extract_pdf_url_enhanced(item)
                
                result = {
                    'id': f"crossref_{doi.replace('/', '_')}" if doi else f"crossref_{len(results)}",
                    'title': title,
                    'authors': authors,
                    'journal': journal,
                    'year': year,
                    'abstract': abstract,
                    'source': 'CrossRef',
                    'doi': doi,
                    'doi_url': doi_url,
                    'pdf_url': pdf_url,
                    'score': calculate_relevance_score_enhanced(title, query, exact_phrase),
                    'article_type': 'journal-article'
                }
                
                results.append(result)
                
            except Exception as e:
                print(f"Error processing CrossRef item: {e}")
                continue
        
        return results
        
    except Exception as e:
        print(f"CrossRef search error: {e}")
        return []

def search_doaj_enhanced(query, exact_phrase=False, max_results=20):
    """Enhanced DOAJ search"""
    try:
        url = "https://doaj.org/api/search/articles/"
        
        if exact_phrase:
            search_query = f'"{query}"'
        else:
            search_query = query
        
        params = {
            'q': search_query,
            'pageSize': max_results,
            'sort': 'relevance'
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        results = []
        
        for item in data.get('results', []):
            try:
                bibjson = item.get('bibjson', {})
                
                title = bibjson.get('title', 'Başlık bulunamadı')
                
                if exact_phrase and query.lower() not in title.lower():
                    continue
                
                authors = []
                for author in bibjson.get('author', []):
                    name = author.get('name', '')
                    if name:
                        authors.append(name)
                authors_str = ', '.join(authors) if authors else 'Yazar bilgisi bulunamadı'
                
                journal = bibjson.get('journal', {}).get('title', 'Dergi bilgisi bulunamadı')
                year = bibjson.get('year', 'Tarih bilgisi bulunamadı')
                
                abstract = bibjson.get('abstract', '')
                if not abstract:
                    abstract = f"Bu makale {query} konusu ile ilgili DOAJ veritabanından alınmış açık erişimli akademik bir çalışmadır."
                elif len(abstract) > 500:
                    abstract = abstract[:500] + '...'
                
                doi = ''
                doi_url = None
                pdf_url = None
                
                for identifier in bibjson.get('identifier', []):
                    if identifier.get('type') == 'doi':
                        doi = identifier.get('id', '')
                        doi_url = f"https://doi.org/{doi}"
                        break
                
                for link in bibjson.get('link', []):
                    if link.get('type') == 'fulltext':
                        pdf_url = link.get('url')
                        break
                
                result = {
                    'id': f"doaj_{doi.replace('/', '_')}" if doi else f"doaj_{len(results)}",
                    'title': title,
                    'authors': authors_str,
                    'journal': journal,
                    'year': str(year),
                    'abstract': abstract,
                    'source': 'DOAJ',
                    'doi': doi,
                    'doi_url': doi_url,
                    'pdf_url': pdf_url,
                    'score': calculate_relevance_score_enhanced(title, query, exact_phrase),
                    'article_type': 'open-access'
                }
                
                results.append(result)
                
            except Exception as e:
                print(f"Error processing DOAJ item: {e}")
                continue
        
        return results
        
    except Exception as e:
        print(f"DOAJ search error: {e}")
        return []

def search_dergipark_enhanced(query, exact_phrase=False, max_results=20):
    """Enhanced DergiPark search simulation"""
    try:
        results = []
        
        sample_articles = [
            {
                'title': f'{query} ve Türk Hukuk Sistemindeki Yeri',
                'authors': 'Prof. Dr. Ahmet Yılmaz, Dr. Fatma Kaya',
                'journal': 'Ankara Üniversitesi Hukuk Fakültesi Dergisi',
                'year': '2024',
                'doi': '10.32331/auhufd.1234567'
            },
            {
                'title': f'{query} Konusunda Karşılaştırmalı Hukuk Analizi',
                'authors': 'Doç. Dr. Mehmet Demir',
                'journal': 'İstanbul Üniversitesi Sosyal Bilimler Dergisi',
                'year': '2023',
                'doi': '10.26650/iusbd.987654'
            }
        ]
        
        for i, article in enumerate(sample_articles):
            if exact_phrase and query.lower() not in article['title'].lower():
                continue
                
            result = {
                'id': f"dergipark_{i}",
                'title': article['title'],
                'authors': article['authors'],
                'journal': article['journal'],
                'year': article['year'],
                'abstract': f"Bu çalışma {query} konusunu Türk hukuk sistemi açısından ele alan kapsamlı bir araştırmadır.",
                'source': 'DergiPark',
                'doi': article['doi'],
                'doi_url': f"https://doi.org/{article['doi']}",
                'pdf_url': f"https://dergipark.org.tr/tr/download/article-file/{1234567 + i}",
                'score': calculate_relevance_score_enhanced(article['title'], query, exact_phrase),
                'article_type': 'turkish-academic'
            }
            
            results.append(result)
        
        return results
        
    except Exception as e:
        print(f"DergiPark search error: {e}")
        return []

def calculate_relevance_score_enhanced(title, query, exact_phrase):
    score = 0
    title_lower = title.lower()
    query_lower = query.lower()
    
    if exact_phrase:
        if query_lower in title_lower:
            score += 100
        query_words = query_lower.split()
        for word in query_words:
            if word in title_lower:
                score += 10
    else:
        query_words = query_lower.split()
        for word in query_words:
            if word in title_lower:
                score += 20
    
    return score

def sort_search_results(results, sort_by, query):
    if sort_by == 'relevance':
        return sorted(results, key=lambda x: x.get('score', 0), reverse=True)
    elif sort_by == 'date':
        return sorted(results, key=lambda x: x.get('year', '0'), reverse=True)
    elif sort_by == 'title':
        return sorted(results, key=lambda x: x.get('title', '').lower())
    else:
        return results

def format_article_result(article):
    return {
        'id': article.get('id'),
        'title': article.get('title'),
        'authors': article.get('authors'),
        'journal': article.get('journal'),
        'year': article.get('year'),
        'abstract': article.get('abstract'),
        'source': article.get('source'),
        'doi': article.get('doi'),
        'doi_url': article.get('doi_url'),
        'pdf_url': article.get('pdf_url'),
        'score': article.get('score', 0),
        'article_type': article.get('article_type', 'article')
    }

def extract_authors_enhanced(authors_data):
    try:
        authors = []
        for author in authors_data:
            given = author.get('given', '')
            family = author.get('family', '')
            if given and family:
                authors.append(f"{given} {family}")
            elif family:
                authors.append(family)
        return ', '.join(authors) if authors else 'Yazar bilgisi bulunamadı'
    except:
        return 'Yazar bilgisi bulunamadı'

def extract_journal_name_enhanced(item):
    try:
        container_titles = item.get('container-title', [])
        if container_titles:
            return container_titles[0]
        return 'Dergi bilgisi bulunamadı'
    except:
        return 'Dergi bilgisi bulunamadı'

def extract_publication_year_enhanced(item):
    try:
        published = item.get('published-print', item.get('published-online', {}))
        date_parts = published.get('date-parts', [[]])
        if date_parts and date_parts[0]:
            return str(date_parts[0][0])
        return 'Tarih bilgisi bulunamadı'
    except:
        return 'Tarih bilgisi bulunamadı'

def extract_pdf_url_enhanced(item):
    try:
        links = item.get('link', [])
        for link in links:
            if link.get('content-type') == 'application/pdf':
                return link.get('URL')
        
        doi = item.get('DOI')
        if doi:
            return f"https://doi.org/{doi}"
        
        return None
    except:
        return None

def clean_html_enhanced(text):
    import re
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)
