# core/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from .models import (
    JudicialDecision, Article, Legislation,
    MevzuatGelismis, MevzuatTuru, MevzuatKategori, 
    MevzuatMadde, MevzuatDegisiklik, MevzuatLog
)
from django.db.models import Q
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
import logging

logger = logging.getLogger(__name__)

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
from .param_simple_service import ParamSimpleService
from .param_shared_payment_service import ParamSharedPaymentService
from .param_modal_service import ParamModalService

def voice_assistant(request):
    """Sesli asistan ana sayfası"""
    return render(request, 'core/voice_assistant.html')

# Admin views import
from .admin_views import admin_pdf_upload, admin_mevzuat_list, admin_delete_mevzuat

# External mevzuat views import
from .external_mevzuat_views import external_mevzuat_detail, external_mevzuat_pdf_proxy

# MCP views removed - feature reverted

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
# from .nlp_utils import analyze_text  # Commented out due to emoji module dependency
from django.http import JsonResponse
from django.shortcuts import render
from django.db.models import Q
from .models import JudicialDecision
# from .nlp_utils import analyze_text  # Commented out due to emoji module dependency
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
        ).order_by('-karar_tarihi')[:10])
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
    """
    Kelime bazlı arama sistemi - her kelimeyi ayrı ayrı arar
    """
    query = request.GET.get('q', '')
    area = request.GET.get('area', 'both')

    judicial_results = JudicialDecision.objects.none()
    legislation_results = Legislation.objects.none()
    article_results = Article.objects.none()

    if query:
        # Sorguyu kelimelere ayır ve boş kelimeleri filtrele
        words = [word.strip() for word in query.split() if word.strip()]
        
        if words and area in ['judicial', 'both']:
            # Her kelime için Q objesi oluştur
            q_objects = Q()
            for word in words:
                q_objects &= (
                    Q(karar_ozeti__icontains=word) |
                    Q(anahtar_kelimeler__icontains=word) |
                    Q(karar_tam_metni__icontains=word)
                )
            judicial_results = JudicialDecision.objects.filter(q_objects)
            
        if words and area in ['legislation', 'both']:
            q_objects = Q()
            for word in words:
                q_objects &= (
                    Q(baslik__icontains=word) |
                    Q(konu__icontains=word)
                )
            legislation_results = Legislation.objects.filter(q_objects)
            
        if words and area in ['articles', 'both']:
            q_objects = Q()
            for word in words:
                q_objects &= (
                    Q(makale_basligi__icontains=word) |
                    Q(makale_ozeti__icontains=word) |
                    Q(makale_metni__icontains=word)
                )
            article_results = Article.objects.filter(q_objects)

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
import logging

logger = logging.getLogger(__name__)


def judicial_decisions_page(request):
    """Ana yargı kararları sayfası - sadece arama formu"""
    context = {
        'newest_decisions': [],
        'query': '',
        'decisions': [],
        'total_decisions': 0
    }
    return render(request, 'core/judicial_decisions.html', context)

def judicial_decisions(request):
    from django.core.cache import cache
    from django.core.paginator import Paginator
    from django.http import JsonResponse
    from django.db import connection
    import time
    
    # AJAX isteği mi kontrol et
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    query = request.GET.get('q', '').strip()
    page_number = request.GET.get('page', 1)
    
    # Initialize variables to avoid UnboundLocalError
    newest_decisions = None
    court_type_counts = {}
    total_decisions = 0
    search_time = 0
    
    # Gelişmiş filtreler
    court_type = request.GET.get('court_type', '').strip()
    chamber = request.GET.get('chamber', '').strip()
    date_range = request.GET.get('date_range', '').strip()
    decision_number = request.GET.get('decision_number', '').strip()
    case_number = request.GET.get('case_number', '').strip()
    sort_order = request.GET.get('sort_order', 'relevance')
    per_page = int(request.GET.get('per_page', '20'))
    
    # Cache anahtarları
    cache_key_counts = 'court_type_counts'
    cache_key_total = 'total_decisions_count'
    cache_key_newest = 'newest_decisions_list'
    
    # Herhangi bir filtre veya arama varsa
    if query or court_type or chamber or date_range or decision_number or case_number:
        # Çok hızlı PostgreSQL search
        start_time = time.time()
        
        with connection.cursor() as cursor:
            # Base SQL
            select_sql = """
                SELECT id, karar_turu, karar_veren_mahkeme, esas_numarasi, 
                       karar_numarasi, karar_tarihi, karar_ozeti"""
            
            from_sql = " FROM core_judicialdecision"
            where_clauses = []
            params = []
            
            # Basit arama
            if query:
                select_sql += ", 1 as rank"
                words = query.split()[:3]  # Max 3 kelime
                for word in words:
                    where_clauses.append("karar_ozeti ILIKE %s")
                    params.append(f"%{word.strip()}%")
            else:
                select_sql += ", 0 as rank"
            
            # Mahkeme türü filtresi
            if court_type:
                where_clauses.append("karar_turu = %s")
                params.append(court_type)
            
            # Daire filtresi
            if chamber:
                where_clauses.append("karar_veren_mahkeme ILIKE %s")
                params.append(f'%{chamber}%')
            
            # Tarih aralığı filtresi
            if date_range:
                from datetime import datetime, timedelta
                today = datetime.now().date()
                
                if date_range == 'today':
                    where_clauses.append("karar_tarihi = %s")
                    params.append(today)
                elif date_range == 'week':
                    where_clauses.append("karar_tarihi >= %s")
                    params.append(today - timedelta(days=7))
                elif date_range == 'month':
                    where_clauses.append("karar_tarihi >= %s")
                    params.append(today - timedelta(days=30))
                elif date_range == '3months':
                    where_clauses.append("karar_tarihi >= %s")
                    params.append(today - timedelta(days=90))
                elif date_range == '6months':
                    where_clauses.append("karar_tarihi >= %s")
                    params.append(today - timedelta(days=180))
                elif date_range == 'year':
                    where_clauses.append("karar_tarihi >= %s")
                    params.append(today - timedelta(days=365))
            
            # Karar numarası filtresi
            if decision_number:
                where_clauses.append("karar_numarasi ILIKE %s")
                params.append(f'%{decision_number}%')
            
            # Esas numarası filtresi
            if case_number:
                where_clauses.append("esas_numarasi ILIKE %s")
                params.append(f'%{case_number}%')
            
            # WHERE clause oluştur
            if where_clauses:
                where_sql = " WHERE " + " AND ".join(where_clauses)
            else:
                where_sql = ""
            
            # ORDER BY
            if sort_order == 'date_desc':
                order_sql = " ORDER BY karar_tarihi DESC"
            elif sort_order == 'date_asc':
                order_sql = " ORDER BY karar_tarihi ASC"
            elif sort_order == 'court_alpha':
                order_sql = " ORDER BY karar_veren_mahkeme ASC"
            elif sort_order == 'decision_number':
                order_sql = " ORDER BY karar_numarasi DESC"
            elif query:  # relevance sıralaması sadece arama varsa
                order_sql = " ORDER BY rank DESC, karar_tarihi DESC"
            else:
                order_sql = " ORDER BY karar_tarihi DESC"
            
            # Sayfa hesaplama
            offset = (int(page_number) - 1) * per_page
            
            # SQL'i birleştir
            full_sql = select_sql + from_sql + where_sql + order_sql + " LIMIT %s OFFSET %s"
            params.extend([per_page, offset])
            
            # Query timeout ayarla (30 saniye)
            cursor.execute("SET statement_timeout = '30s'")
            
            # Performance için LIMIT optimize et
            max_search_limit = 10000  # Çok büyük sonuçları sınırla
            
            try:
                cursor.execute(full_sql, params)
                results = cursor.fetchall()
                
                # Toplam sonuç sayısı için optimize edilmiş count
                # Çok büyük sonuçlar için estimate kullan
                if where_clauses:  # Filtre varsa tam count
                    count_sql = "SELECT COUNT(*) FROM core_judicialdecision" + where_sql
                    count_params = params[:-2] if params else []
                    # Aynı parametreleri stats için de kullan
                    stats_count_params = count_params
                    cursor.execute(count_sql, count_params)
                    total_results = cursor.fetchone()[0]
                    
                    # Çok büyük sonuç setlerini sınırla
                    if total_results > max_search_limit:
                        total_results = max_search_limit
                else:  # Filtre yoksa estimate count kullan (çok hızlı)
                    cursor.execute("SELECT reltuples::BIGINT AS estimate FROM pg_class WHERE relname = 'core_judicialdecision'")
                    total_results = cursor.fetchone()[0] or 0
                
            except Exception as e:
                # Query timeout veya hata durumunda boş sonuç döndür
                logger = logging.getLogger(__name__)
                logger.error(f"Query: {query}, Total Results: {total_results}, SQL: {full_sql[:200]}")
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Database query error: {str(e)}")
                results = []
                total_results = 0
                count_params = []
            finally:
                # Timeout'u resetle
                stats_count_params = []
                cursor.execute("RESET statement_timeout")
        
        # Sonuçları Django objelerine çevir
        decisions = []
        for row in results:
            decision = type('Decision', (), {
                'id': row[0],
                'karar_turu': row[1],
                'karar_veren_mahkeme': row[2],
                'esas_numarasi': row[3],
                'karar_numarasi': row[4],
                'karar_tarihi': row[5],
                'karar_ozeti': row[6],
                'relevance_score': row[7] if len(row) > 7 else 0
            })
            decisions.append(decision)
        print(f"Added decision to list. Total: {len(decisions)}")
        
        # Sayfalama nesnesi oluştur
        from django.core.paginator import Page
        paginator = Paginator(range(total_results), per_page)
        page_obj = paginator.get_page(page_number)
        
        # Mahkeme türü istatistikleri (cache'li)
        filter_key = f"{query}_{court_type}_{chamber}_{date_range}_{decision_number}_{case_number}"
        cache_key_search_stats = f'search_stats_{hash(filter_key)}'
        court_type_counts = cache.get(cache_key_search_stats)
        
        if court_type_counts is None:
            with connection.cursor() as cursor:
                pass  # Placeholder
                #                 stats_sql = "SELECT karar_turu, COUNT(*) as total FROM core_judicialdecision" + where_sql + " GROUP BY karar_turu"
                #                 # count_params tanımını güvenli hale getir
                #                 safe_count_params = count_params if "count_params" in locals() and len(count_params) > 0 else []
                #                 cursor.execute(stats_sql, safe_count_params)
                #                 court_type_counts = {row[0]: row[1] for row in cursor.fetchall()}
                #             cache.set(cache_key_search_stats, court_type_counts, 300)  # 5 dakika
        
        search_time = round((time.time() - start_time) * 1000, 2)
        court_type_counts = {}
        
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
                    'relevance_score': round(d.relevance_score, 3)
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
        
        # Custom page object
        class PageObj:
            def __init__(self, decisions, page_obj):
                self.object_list = decisions
                self.number = page_obj.number
                self.paginator = page_obj.paginator
                self._page_obj = page_obj
                
            def has_other_pages(self):
                return self._page_obj.has_other_pages()
                
            def has_previous(self):
                return self._page_obj.has_previous()
                
            def has_next(self):
                return self._page_obj.has_next()
                
            def previous_page_number(self):
                return self._page_obj.previous_page_number() if self._page_obj.has_previous() else None
                
            def next_page_number(self):
                return self._page_obj.next_page_number() if self._page_obj.has_next() else None
                
            def __iter__(self):
                return iter(self.object_list)
                
            def __len__(self):
                return len(self.object_list)
        
        try:
            newest_decisions = PageObj(decisions, page_obj)
        except Exception as e:
            # Fallback if PageObj creation fails
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"PageObj creation error: {str(e)}")
            newest_decisions = decisions[:15]  # Simple fallback
        
        total_decisions = total_results
        
    else:
        # Arama yoksa cache kullan
        court_type_counts = cache.get(cache_key_counts)
        total_decisions = cache.get(cache_key_total)
        newest_decisions_list = cache.get(cache_key_newest)
        
        if court_type_counts is None or total_decisions is None or newest_decisions_list is None:
            all_queryset = JudicialDecision.objects.all()
            
            court_type_counts_qs = all_queryset.values('karar_turu').annotate(total=Count('id'))
            court_type_counts = {item['karar_turu']: item['total'] for item in court_type_counts_qs}
            
            total_decisions = all_queryset.count()
            
            newest_decisions_list = list(
                all_queryset.select_related().only(
                    'id', 'karar_turu', 'karar_veren_mahkeme', 'esas_numarasi', 
                    'karar_numarasi', 'karar_tarihi', 'karar_ozeti'
                ).order_by('-karar_tarihi')[:100]
            )
            
            cache.set(cache_key_counts, court_type_counts, 1800)
            cache.set(cache_key_total, total_decisions, 1800)
            cache.set(cache_key_newest, newest_decisions_list, 1800)
        
        paginator = Paginator(newest_decisions_list, 20)
        newest_decisions = paginator.get_page(page_number)
        search_time = 0

    # Herhangi bir filtre var mı kontrol et
    has_any_filter = bool(query or court_type or chamber or date_range or decision_number or case_number)
    
    # Final safety check for newest_decisions
    if newest_decisions is None:
        newest_decisions = []
    
    context = {
        'query': query,
        'newest_decisions': decisions if query else newest_decisions,
        'court_type_counts': court_type_counts,
        'total_decisions': total_decisions,
        'is_paginated': getattr(newest_decisions, 'has_other_pages', lambda: False)(),
        'search_time': locals().get('search_time', 0),
        'has_filters': has_any_filter,
        'court_type': court_type,
        'chamber': chamber,
        'date_range': date_range,
        'decision_number': decision_number,
        'case_number': case_number,
        'sort_order': sort_order,
        'per_page': per_page,
        'page_obj': newest_decisions,
        'smart_page_range': [],    }
    return render(request, "core/search_results.html", context)


def articles(request):
    """Harici kaynaklardan makale arama ana sayfası"""
    context = {}
    return render(request, 'core/articles.html', context)


def article_detail(request, pk):
    """Makale detay sayfası"""
    from .models import Article
    article = get_object_or_404(Article, pk=pk)
    context = {'article': article}
    return render(request, 'core/article_detail.html', context)
