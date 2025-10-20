def legislation_results(request):
    """
    Mevzuat arama sonuçları - SimpleWorkingMevzuat ile
    """
    from .simple_working_mevzuat import SimpleWorkingMevzuat
    
    query = request.GET.get('q', '').strip()
    page = int(request.GET.get('page', 1))
    
    if not query:
        return render(request, 'core/legislation_results.html', {
            'query': '',
            'results': [],
            'error': 'Arama terimi giriniz'
        })
    
    # SimpleWorkingMevzuat servisi ile arama yap
    service = SimpleWorkingMevzuat()
    search_result = service.search_legislation(query, page=page)
    
    # Template'e gönder
    context = {
        'query': query,
        'results': search_result.get('results', []),
        'total_count': search_result.get('total', 0),
        'page': page,
        'has_results': len(search_result.get('results', [])) > 0,
        'error': search_result.get('error') if not search_result.get('success') else None
    }
    
    return render(request, 'core/legislation_results.html', context)