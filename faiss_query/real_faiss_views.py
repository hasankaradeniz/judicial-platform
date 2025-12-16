def karar_listesi(request):
    """REAL FAISS Integration - No more test results!"""
    
    olay = request.session.get('olay')
    hukuki_aciklama = request.session.get('hukuki_aciklama')
    
    if not olay:
        return redirect('faiss_query:olay_gir')

    print(f"🔍 REAL FAISS SEARCH for: {olay}")

    try:
        # Use REAL hierarchical FAISS
        from core.hierarchical_faiss_manager import FixedHierarchicalFAISSManager
        
        manager = FixedHierarchicalFAISSManager()
        
        # Get real results
        hierarchical_results = manager.search_hierarchical(olay, k=50)
        detected_areas = manager.detect_legal_area(olay)
        
        print(f"✅ REAL FAISS found {len(hierarchical_results)} results")
        print(f"✅ Detected legal areas: {detected_areas}")
        
        # Convert hierarchical results to view format
        converted_results = []
        for i, result in enumerate(hierarchical_results):
            combined_score = result['similarity_score']
            idx = i
            
            # Real karar data from FAISS
            karar_data = {
                'id': result.get('decision_id', i),
                'mahkeme': result.get('mahkeme', 'Bilinmeyen Mahkeme'),
                'tarih': result.get('tarih', ''),
                'sayi': result.get('sayi', ''),
                'text': result.get('full_text', result.get('text_snippet', '')),
                'esas_no': result.get('esas_no', 'N/A'),
                'karar_no': result.get('karar_no', 'N/A'),
                'ozet': result.get('text_snippet', result.get('full_text', ''))[:300] + '...' if result.get('text_snippet') or result.get('full_text') else 'Özet mevcut değil'
            }
            
            alan_adi = result['legal_area']
            relevance_score = result['similarity_score'] * 10  # 0-100 scale
            
            converted_results.append((combined_score, idx, karar_data, alan_adi, relevance_score))
        
        # Use REAL results
        sorted_results = sorted(converted_results, key=lambda x: x[4], reverse=True)[:50]
        
        print(f"✅ Using {len(sorted_results)} REAL FAISS results")
        
        if len(sorted_results) == 0:
            print("⚠️ No results found even with hierarchical FAISS")
        
    except Exception as e:
        print(f"❌ REAL FAISS error: {e}")
        import traceback
        traceback.print_exc()
        
        # If FAISS fails, return empty results instead of fake ones
        sorted_results = []
        detected_areas = ['hukuk']

    # Pagination
    paginator = Paginator(sorted_results, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Debug info with REAL data
    debug_info = {
        'total_results': len(sorted_results),
        'processed_categories': len(detected_areas),
        'keywords': detected_areas,
        'min_score': min([r[4] for r in sorted_results]) if sorted_results else 0,
        'max_score': max([r[4] for r in sorted_results]) if sorted_results else 0,
        'test_mode': False,  # This is REAL mode
        'search_type': 'hierarchical_faiss'
    }

    print(f"🔍 REAL FAISS DEBUG: {len(sorted_results)} results, page count: {page_obj.paginator.count}")

    return render(request, 'faiss_query/karar_listesi.html', {
        'olay': olay,
        'hukuki_aciklama': hukuki_aciklama,
        'page_obj': page_obj,
        'legal_keywords': detected_areas,
        'debug_info': debug_info,
    })