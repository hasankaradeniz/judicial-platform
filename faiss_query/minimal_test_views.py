def karar_listesi(request):
    """Minimal test version to ensure results are shown"""
    olay = request.session.get('olay')
    hukuki_aciklama = request.session.get('hukuki_aciklama')
    if not olay:
        return redirect('faiss_query:olay_gir')

    # Create fake test results to ensure template works
    fake_results = []
    for i in range(5):
        combined_score = 0.8 - (i * 0.1)
        idx = i
        karar_data = {
            'id': f'test_{i}',
            'mahkeme': f'Test Mahkemesi {i+1}',
            'tarih': '2024-01-01',
            'sayi': f'2024/{i+1}',
            'text': f'Bu bir test kararıdır. Miras hukuku ile ilgili örnek metin {i+1}. Gayrimenkul devri ve iptal konuları işlenmektedir.',
            'esas_no': f'2024/{i+1} Esas',
            'karar_no': f'2024/{i+1} Karar',
            'ozet': f'Test kararı {i+1} - Miras hukuku, gayrimenkul devri ve iptal konuları hakkında.'
        }
        alan_adi = 'oh_medeni_hukuk_miras_hukuku'
        relevance_score = 90 - (i * 10)
        
        fake_results.append((combined_score, idx, karar_data, alan_adi, relevance_score))

    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(fake_results, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Debug info
    debug_info = {
        'total_results': len(fake_results),
        'processed_categories': 1,
        'keywords': ['miras', 'gayrimenkul', 'devir', 'iptal'],
        'min_score': 50,
        'max_score': 90,
        'test_mode': True
    }

    return render(request, 'faiss_query/karar_listesi.html', {
        'olay': olay,
        'hukuki_aciklama': hukuki_aciklama,
        'page_obj': page_obj,
        'legal_keywords': ['miras', 'gayrimenkul', 'devir', 'iptal'],
        'debug_info': debug_info,
    })