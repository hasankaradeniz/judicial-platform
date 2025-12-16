def karar_listesi(request):
    """ABSOLUTELY REAL - No more fake data mapping!"""
    
    olay = request.session.get('olay')
    hukuki_aciklama = request.session.get('hukuki_aciklama')
    
    if not olay:
        return redirect('faiss_query:olay_gir')

    print(f"🔍 ABSOLUTELY REAL FAISS SEARCH for: {olay}")

    try:
        # Use REAL hierarchical FAISS
        from core.hierarchical_faiss_manager import FixedHierarchicalFAISSManager
        
        manager = FixedHierarchicalFAISSManager()
        
        # Get REAL results
        hierarchical_results = manager.search_hierarchical(olay, k=50)
        detected_areas = manager.detect_legal_area(olay)
        
        print(f"✅ REAL FAISS returned {len(hierarchical_results)} results")
        print(f"✅ Detected areas: {detected_areas}")
        
        # Convert REAL data structure to template format
        converted_results = []
        for i, result in enumerate(hierarchical_results):
            # Use EXACTLY what comes from FAISS - no fabrication!
            combined_score = result['similarity_score']
            idx = i
            
            # Map REAL FAISS data fields directly
            karar_data = {
                'id': result['decision_id'],  # Real decision ID
                'mahkeme': result['mahkeme'],  # Real court name
                'tarih': result['tarih'],      # Real date
                'sayi': result.get('sayi', ''),  # Real case number
                'text': result.get('text_snippet', result.get('full_text', '')),  # Real text
                'esas_no': result.get('esas_no', ''),  # Real esas number
                'karar_no': result.get('karar_no', ''),  # Real karar number  
                'ozet': result.get('text_snippet', '')[:300] + '...' if result.get('text_snippet') else 'Özet mevcut değil'
            }
            
            alan_adi = result['legal_area']
            relevance_score = result['similarity_score'] * 10  # Convert to 0-100 scale
            
            converted_results.append((combined_score, idx, karar_data, alan_adi, relevance_score))
        
        # Sort by score
        sorted_results = sorted(converted_results, key=lambda x: x[4], reverse=True)[:50]
        
        print(f"✅ Converted {len(sorted_results)} REAL results to template format")
        
        # Debug: Print first real result
        if sorted_results:
            first_result = sorted_results[0][2]  # karar_data
            print(f"📋 First REAL result: Court={first_result['mahkeme']}, Date={first_result['tarih']}, ID={first_result['id']}")
        
    except Exception as e:
        print(f"❌ REAL FAISS error: {e}")
        import traceback
        traceback.print_exc()
        sorted_results = []
        detected_areas = ['error']

    # Pagination
    paginator = Paginator(sorted_results, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Debug info with real data
    debug_info = {
        'total_results': len(sorted_results),
        'processed_categories': len(detected_areas),
        'keywords': detected_areas,
        'min_score': min([r[4] for r in sorted_results]) if sorted_results else 0,
        'max_score': max([r[4] for r in sorted_results]) if sorted_results else 0,
        'test_mode': False,
        'search_type': 'absolutely_real_hierarchical_faiss'
    }

    print(f"🔍 REAL DEBUG: {len(sorted_results)} results, page count: {page_obj.paginator.count}")

    return render(request, 'faiss_query/karar_listesi.html', {
        'olay': olay,
        'hukuki_aciklama': hukuki_aciklama,
        'page_obj': page_obj,
        'legal_keywords': detected_areas,
        'debug_info': debug_info,
    })