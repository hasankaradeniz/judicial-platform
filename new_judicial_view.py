def judicial_decisions(request):
    from django.core.cache import cache
    from django.core.paginator import Paginator
    from django.http import JsonResponse
    from django.db import connection
    import time
    
    # AJAX isteği mi kontrol et
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    # Tüm filtre parametrelerini al
    query = request.GET.get('q', '').strip()
    court_type = request.GET.get('court_type', '').strip()
    case_number = request.GET.get('case_number', '').strip()
    decision_number = request.GET.get('decision_number', '').strip()
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()
    page_number = request.GET.get('page', 1)
    
    # Cache anahtarları
    cache_key_counts = 'court_type_counts'
    cache_key_total = 'total_decisions_count'
    cache_key_newest = 'newest_decisions_list'
    
    # Herhangi bir filtre var mı kontrol et
    has_any_filter = any([query, court_type, case_number, decision_number, date_from, date_to])
    
    if has_any_filter:
        # Gelişmiş filtreleme ile PostgreSQL arama
        start_time = time.time()
        
        with connection.cursor() as cursor:
            # Query timeout ayarla (30 saniye)
            cursor.execute("SET statement_timeout = '30s'")
            
            # Dinamik SQL sorgu oluştur
            where_conditions = []
            params = []
            rank_needed = False
            
            # Full-text arama (eğer query varsa)
            if query:
                where_conditions.append("""
                    to_tsvector('turkish', COALESCE(karar_ozeti, '') || ' ' || 
                                         COALESCE(anahtar_kelimeler, '') || ' ' || 
                                         COALESCE(karar_tam_metni, '')) 
                    @@ plainto_tsquery('turkish', %s)
                """)
                params.append(query)
                rank_needed = True
            
            # Mahkeme türü filtresi
            if court_type:
                where_conditions.append("karar_turu ILIKE %s")
                params.append(f'%{court_type}%')
            
            # Esas numarası filtresi
            if case_number:
                where_conditions.append("esas_numarasi ILIKE %s")
                params.append(f'%{case_number}%')
            
            # Karar numarası filtresi
            if decision_number:
                where_conditions.append("karar_numarasi ILIKE %s")
                params.append(f'%{decision_number}%')
            
            # Tarih aralığı filtreleri
            if date_from:
                where_conditions.append("karar_tarihi >= %s")
                params.append(date_from)
            
            if date_to:
                where_conditions.append("karar_tarihi <= %s")
                params.append(date_to)
            
            # WHERE clause'u oluştur
            where_clause = ""
            if where_conditions:
                where_clause = "WHERE " + " AND ".join(where_conditions)
            
            # Performance için LIMIT optimize et
            max_search_limit = 10000  # Çok büyük sonuçları sınırla
            per_page = 20
            offset = (int(page_number) - 1) * per_page
            limit_with_offset = min(per_page + offset, max_search_limit)
            
            # Rank kısmını hazırla
            if rank_needed:
                rank_select = "ts_rank(to_tsvector('turkish', COALESCE(karar_ozeti, '') || ' ' || COALESCE(anahtar_kelimeler, '') || ' ' || COALESCE(karar_tam_metni, '')), plainto_tsquery('turkish', %s))"
                order_by = "ORDER BY rank DESC, karar_tarihi DESC"
                # Rank için ekstra parametre
                search_params_for_rank = [query] + params
            else:
                rank_select = "1.0"
                order_by = "ORDER BY karar_tarihi DESC"
                search_params_for_rank = params
            
            # Ana arama sorgusu
            search_sql = f"""
                SELECT id, karar_turu, karar_veren_mahkeme, esas_numarasi, 
                       karar_numarasi, karar_tarihi, karar_ozeti,
                       {rank_select} as rank
                FROM core_judicialdecision 
                {where_clause}
                {order_by}
                LIMIT %s OFFSET %s
            """
            
            # Parametreleri hazırla
            final_params = search_params_for_rank + [per_page, offset]
            
            cursor.execute(search_sql, final_params)
            results = cursor.fetchall()
            
            # Toplam sonuç sayısı (max_search_limit ile sınırlı)
            count_sql = f"""
                SELECT COUNT(*) FROM (
                    SELECT 1 FROM core_judicialdecision 
                    {where_clause}
                    LIMIT {max_search_limit}
                ) as limited_results
            """
            cursor.execute(count_sql, params)
            total_results = cursor.fetchone()[0]
        
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
                'relevance_score': row[7]
            })()
            decisions.append(decision)
        
        # Sayfalama nesnesi oluştur
        from django.core.paginator import Page
        paginator = Paginator(range(total_results), per_page)
        page_obj = paginator.get_page(page_number)
        
        # Mahkeme türü istatistikleri
        filter_cache_key = f'filter_stats_{hash(str(params))}'
        court_type_counts = cache.get(filter_cache_key)
        
        if court_type_counts is None:
            with connection.cursor() as cursor:
                stats_sql = f"""
                    SELECT karar_turu, COUNT(*) as total FROM (
                        SELECT karar_turu FROM core_judicialdecision 
                        {where_clause}
                        LIMIT {max_search_limit}
                    ) as limited_stats
                    GROUP BY karar_turu
                """
                cursor.execute(stats_sql, params)
                court_type_counts = {row[0]: row[1] for row in cursor.fetchall()}
            cache.set(filter_cache_key, court_type_counts, 300)  # 5 dakika
        
        search_time = round((time.time() - start_time) * 1000, 2)
        
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
        
        newest_decisions = PageObj(decisions, page_obj)
        total_decisions = total_results
        
    else:
        # Hiç filtre yoksa cache kullan
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

    context = {
        'query': query,
        'court_type': court_type,
        'case_number': case_number, 
        'decision_number': decision_number,
        'date_from': date_from,
        'date_to': date_to,
        'newest_decisions': newest_decisions,
        'court_type_counts': court_type_counts,
        'total_decisions': total_decisions,
        'is_paginated': getattr(newest_decisions, 'has_other_pages', lambda: False)(),
        'search_time': locals().get('search_time', 0),
        'has_filters': has_any_filter,
    }
    return render(request, 'core/judicial_decisions.html', context)

