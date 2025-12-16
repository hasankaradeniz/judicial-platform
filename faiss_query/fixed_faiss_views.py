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
            
            # Karar verisini template'in beklediği formatta hazırla
            karar_data = {
                'id': result.get('decision_id', i),
                'mahkeme': result.get('mahkeme', 'Bilinmeyen'),
                'tarih': result.get('tarih', ''),
                'sayi': result.get('sayi', ''),
                'esas_no': result.get('esas_no', 'N/A'),
                'karar_no': result.get('karar_no', 'N/A'),
                'text': result.get('full_text', result.get('text_snippet', '')),
                'ozet': result.get('text_snippet', result.get('full_text', ''))[:300] + '...' if result.get('text_snippet') or result.get('full_text') else 'Özet mevcut değil'
            }
            
            alan_adi = result['legal_area']
            relevance_score = result['similarity_score'] * 10  # 0-100 scale
            
            # İndex ID'sini hierarchical formatta sakla
            idx = f"{alan_adi}_{result.get('decision_id', i)}"
            
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


def karar_detay(request, alan, index):
    """Hierarchical FAISS için güncellenmiş detay görünümü"""
    olay = request.session.get('olay')
    if not olay:
        return redirect('faiss_query:olay_gir')

    page = request.GET.get('page', 1)

    try:
        # Hierarchical yapıda index format: "alan_decision_id"
        if '_' in str(index):
            parts = str(index).split('_')
            area_name = '_'.join(parts[:-1])
            decision_id = parts[-1]
        else:
            area_name = alan
            decision_id = index

        # Hierarchical FAISS manager kullan
        from core.hierarchical_faiss_manager import FixedHierarchicalFAISSManager
        manager = FixedHierarchicalFAISSManager()
        
        # İlgili alanı yükle
        area_data = manager.load_index(area_name)
        if not area_data:
            # Fallback: eski sistemi dene
            alan_data = load_faiss_index(alan)
            if not alan_data:
                return redirect('faiss_query:karar_listesi')
                
            # Eski sistem ile devam et
            try:
                index_int = int(index)
            except ValueError:
                return redirect('faiss_query:karar_listesi')

            mapping = alan_data["mapping"]
            if index_int < 0 or index_int >= len(mapping):
                return redirect('faiss_query:karar_listesi')

            karar = mapping[index_int]
        else:
            # Hierarchical sistemde decision_id ile ara
            mapping = area_data['mapping']
            karar = None
            
            # Mapping yapısını kontrol et
            if isinstance(mapping, dict) and 'metadata' in mapping:
                actual_mapping = mapping['metadata']
            else:
                actual_mapping = mapping
            
            # Decision ID ile karar bul
            for item in actual_mapping:
                if str(item.get('id', item.get('decision_id', ''))) == str(decision_id):
                    karar = item
                    break
                    
            if not karar:
                return redirect('faiss_query:karar_listesi')

        return render(request, 'faiss_query/karar_detay.html', {
            'karar': karar,
            'alan': alan,
            'index': index,
            'page': page,
            'olay': olay
        })
        
    except Exception as e:
        print(f"Karar detay error: {e}")
        return redirect('faiss_query:karar_listesi')