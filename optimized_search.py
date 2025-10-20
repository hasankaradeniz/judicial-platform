# Kelime bazlı arama için SQL optimizasyonu
def build_word_search_query(query):
    """Kelime bazlı arama için PostgreSQL TSVECTOR kullanımı"""
    words = [word.strip() for word in query.split() if word.strip()]
    if not words:
        return "", []
    
    # PostgreSQL full-text search için
    search_terms = ' & '.join(words)
    
    sql_clause = """
        (to_tsvector('turkish', COALESCE(karar_ozeti, '')) @@ to_tsquery('turkish', %s) OR
         to_tsvector('turkish', COALESCE(anahtar_kelimeler, '')) @@ to_tsquery('turkish', %s) OR
         to_tsvector('turkish', COALESCE(karar_tam_metni, '')) @@ to_tsquery('turkish', %s))
    """
    
    return sql_clause, [search_terms, search_terms, search_terms]

# Cache ile sayfalama optimizasyonu
def get_cached_search_results(cache_key, query_func, timeout=300):
    """Arama sonuçlarını cache'le"""
    from django.core.cache import cache
    
    results = cache.get(cache_key)
    if results is None:
        results = query_func()
        cache.set(cache_key, results, timeout)
    return results
EOF < /dev/null