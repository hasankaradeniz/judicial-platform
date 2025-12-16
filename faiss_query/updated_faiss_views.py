# Updated FAISS Query Views - Hierarchical Integration

def karar_listesi(request):
    """Hierarchical FAISS sistemi ile güncellenmiş karar listesi"""
    olay = request.session.get('olay')
    hukuki_aciklama = request.session.get('hukuki_aciklama')
    if not olay:
        return redirect('faiss_query:olay_gir')

    # Yeni hierarchical sistemi kullan
    from core.hierarchical_faiss_manager import FixedHierarchicalFAISSManager
    
    try:
        # Hierarchical FAISS manager oluştur
        manager = FixedHierarchicalFAISSManager()
        
        # Hierarchical arama yap
        results = manager.search_hierarchical(olay, k=50)
        detected_areas = manager.detect_legal_area(olay)
        
        # Sonuçları FAISS query formatına dönüştür
        converted_results = []
        for i, result in enumerate(results):
            # FAISS query beklediği format
            combined_score = result['similarity_score']
            idx = i  # Index simulation
            karar_data = {
                'id': result.get('decision_id', i),
                'mahkeme': result.get('mahkeme', 'Bilinmeyen'),
                'tarih': result.get('tarih', ''),
                'sayi': result.get('sayi', ''),
                'text': result.get('full_text', result.get('text_snippet', ''))
            }
            alan_adi = result['legal_area']
            relevance_score = result['similarity_score'] * 10  # 0-100 scale
            
            converted_results.append((combined_score, idx, karar_data, alan_adi, relevance_score))
        
        # Pagination
        from django.core.paginator import Paginator
        paginator = Paginator(converted_results, 15)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        # Debug bilgisi
        debug_info = {
            'total_results': len(converted_results),
            'detected_areas': detected_areas,
            'search_type': 'hierarchical_faiss',
            'min_score': min([r[4] for r in converted_results]) if converted_results else 0,
            'max_score': max([r[4] for r in converted_results]) if converted_results else 0,
        }

        return render(request, 'faiss_query/karar_listesi.html', {
            'olay': olay,
            'hukuki_aciklama': hukuki_aciklama,
            'page_obj': page_obj,
            'legal_keywords': detected_areas,  # Detected areas as keywords
            'debug_info': debug_info,
        })
        
    except Exception as e:
        # Hata durumunda fallback
        print(f"Hierarchical FAISS error: {e}")
        
        # Boş sonuç döndür ama hata mesajı ile
        debug_info = {
            'total_results': 0,
            'error': str(e),
            'search_type': 'error'
        }
        
        return render(request, 'faiss_query/karar_listesi.html', {
            'olay': olay,
            'hukuki_aciklama': hukuki_aciklama,
            'page_obj': None,
            'legal_keywords': [],
            'debug_info': debug_info,
        })