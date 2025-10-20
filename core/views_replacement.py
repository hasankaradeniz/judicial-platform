def judicial_decisions(request):
    from django.core.cache import cache
    from django.core.paginator import Paginator
    from django.http import JsonResponse
    from django.db import connection
    from django.db.models import Count
    import time
    
    # AJAX isteği mi kontrol et
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    # Filter parameters
    query = request.GET.get('q', '').strip()
    court_type = request.GET.get('court_type', '').strip()
    chamber = request.GET.get('chamber', '').strip() 
    decision_number = request.GET.get('decision_number', '').strip()
    case_number = request.GET.get('case_number', '').strip()
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()
    date_range = request.GET.get('date_range', '').strip()
    page_number = request.GET.get('page', 1)
    
    # Cache anahtarları
    cache_key_counts = 'court_type_counts'
    cache_key_total = 'total_decisions_count'
    cache_key_newest = 'newest_decisions_list'
    
    # Build WHERE conditions
    where_conditions = []
    params = []
    
    # Text search condition
    if query:
        where_conditions.append("""
            to_tsvector('turkish', COALESCE(karar_ozeti, '') || ' ' || 
                                 COALESCE(anahtar_kelimeler, '') || ' ' || 
                                 COALESCE(karar_tam_metni, '')) 
            @@ plainto_tsquery('turkish', %s)
        """)
        params.append(query)
    
    # Court type filter (mahkeme türü -> karar_turu)
    if court_type:
        if court_type.lower() == 'yargitay':
            where_conditions.append("UPPER(karar_turu) LIKE %s")
            params.append('%YARGITAY%')
        elif court_type.lower() == 'danistay':
            where_conditions.append("UPPER(karar_turu) LIKE %s") 
            params.append('%DANİŞTAY%')
        elif court_type.lower() == 'aym':
            where_conditions.append("UPPER(karar_turu) LIKE %s")
            params.append('%ANAYASA%')
        elif court_type.lower() == 'bolge':
            where_conditions.append("UPPER(karar_turu) LIKE %s")
            params.append('%BÖLGE%')
        else:
            where_conditions.append("UPPER(karar_turu) LIKE %s")
            params.append(f'%{court_type.upper()}%')
    
    # Chamber filter (daire -> karar_veren_mahkeme)
    if chamber:
        where_conditions.append("UPPER(karar_veren_mahkeme) LIKE %s")
        params.append(f'%{chamber.upper()}%')
    
    # Decision number filter (karar numarası -> karar_numarasi)
    if decision_number:
        where_conditions.append("karar_numarasi ILIKE %s")
        params.append(f'%{decision_number}%')
    
    # Case number filter (esas numarası -> esas_numarasi) 
    if case_number:
        where_conditions.append("esas_numarasi ILIKE %s")
        params.append(f'%{case_number}%')
    
    # Date filters (tarih -> karar_tarihi)
    if date_from:
        where_conditions.append("karar_tarihi >= %s")
        params.append(date_from)
    
    if date_to:
        where_conditions.append("karar_tarihi <= %s")
        params.append(date_to)
    
    # Date range presets
    if date_range and not date_from and not date_to:
        from datetime import datetime, timedelta
        today = datetime.now().date()
        
        if date_range == 'last_6_months':
            date_from = today - timedelta(days=180)
            where_conditions.append("karar_tarihi >= %s")
            params.append(date_from)
        elif date_range == 'last_year':
            date_from = today - timedelta(days=365)
            where_conditions.append("karar_tarihi >= %s")
            params.append(date_from)
        elif date_range == 'last_2_years':
            date_from = today - timedelta(days=730)
            where_conditions.append("karar_tarihi >= %s")
            params.append(date_from)
        elif date_range == '2020_onwards':
            where_conditions.append("karar_tarihi >= %s")
            params.append('2020-01-01')
        elif date_range == '2015_onwards':
            where_conditions.append("karar_tarihi >= %s")
            params.append('2015-01-01')
    
    # Check if any filter is applied
    has_any_filter = query or court_type or chamber or decision_number or case_number or date_from or date_to or date_range
    
    if has_any_filter:
        # Build WHERE clause
        where_clause = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        
        # Main search query with filters
        start_time = time.time()
        
        with connection.cursor() as cursor:
            # Select with ranking if text search exists
            if query:
                search_sql = f"""
                    SELECT id, karar_turu, karar_veren_mahkeme, esas_numarasi, 
                           karar_numarasi, karar_tarihi, karar_ozeti,
                           ts_rank(to_tsvector('turkish', COALESCE(karar_ozeti, '') || ' ' || 
                                             COALESCE(anahtar_kelimeler, '') || ' ' || 
                                             COALESCE(karar_tam_metni, '')), 
                                  plainto_tsquery('turkish', %s)) as rank
                    FROM core_judicialdecision 
                    {where_clause}
                    ORDER BY rank DESC, karar_tarihi DESC
                    LIMIT %s OFFSET %s
                """
                count_sql = f"""
                    SELECT COUNT(*) FROM core_judicialdecision 
                    {where_clause}
                """
            else:
                search_sql = f"""
                    SELECT id, karar_turu, karar_veren_mahkeme, esas_numarasi, 
                           karar_numarasi, karar_tarihi, karar_ozeti, 0 as rank
                    FROM core_judicialdecision 
                    {where_clause}
                    ORDER BY karar_tarihi DESC
                    LIMIT %s OFFSET %s
                """
                count_sql = f"""
                    SELECT COUNT(*) FROM core_judicialdecision 
                    {where_clause}
                """
            
            # Pagination
            per_page = 20
            offset = (int(page_number) - 1) * per_page
            
            # Execute search
            search_params = params + [per_page, offset]
            cursor.execute(search_sql, search_params)
            results = cursor.fetchall()
            
            # Execute count
            cursor.execute(count_sql, params)
            total_results = cursor.fetchone()[0]
        
        # Convert results to objects
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
        
        # Pagination object
        from django.core.paginator import Page
        paginator = Paginator(range(total_results), per_page)
        page_obj = paginator.get_page(page_number)
        
        # Court type statistics for filtered results
        cache_key_search_stats = f'search_stats_{hash(str(params))}'
        court_type_counts = cache.get(cache_key_search_stats)
        
        if court_type_counts is None:
            with connection.cursor() as cursor:
                stats_sql = f"""
                    SELECT karar_turu, COUNT(*) as total FROM core_judicialdecision 
                    {where_clause}
                    GROUP BY karar_turu
                """
                cursor.execute(stats_sql, params)
                court_type_counts = {row[0]: row[1] for row in cursor.fetchall()}
            cache.set(cache_key_search_stats, court_type_counts, 300)  # 5 minutes
        
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
        
        # Custom page object for template
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
        # No filters applied - use cache
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
        'chamber': chamber,
        'decision_number': decision_number,
        'case_number': case_number,
        'date_from': date_from,
        'date_to': date_to,
        'date_range': date_range,
        'newest_decisions': newest_decisions,
        'court_type_counts': court_type_counts,
        'total_decisions': total_decisions,
        'is_paginated': getattr(newest_decisions, 'has_other_pages', lambda: False)(),
        'search_time': locals().get('search_time', 0),
    }
    return render(request, 'core/judicial_decisions.html', context)