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
    
    # Initialize variables
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
    
    # Cache keys
    cache_key_counts = 'court_type_counts'
    cache_key_total = 'total_decisions_count'
    cache_key_newest = 'newest_decisions_list'
    
    # Herhangi bir filtre veya arama varsa
    if query or court_type or chamber or date_range or decision_number or case_number:
        start_time = time.time()
        
        with connection.cursor() as cursor:
            # Base SQL
            select_sql = 
