def improved_combined_search_results(request):
    """
    Kelime bazlı arama sistemi - her kelimeyi ayrı ayrı arar
    """
    query = request.GET.get('q', '')
    area = request.GET.get('area', 'both')

    judicial_results = JudicialDecision.objects.none()
    legislation_results = Legislation.objects.none()
    article_results = Article.objects.none()

    if query:
        # Sorguyu kelimelere ayır ve boş kelimeleri filtrele
        words = [word.strip() for word in query.split() if word.strip()]
        
        if words and area in ['judicial', 'both']:
            # Her kelime için Q objesi oluştur
            q_objects = Q()
            for word in words:
                q_objects &= (
                    Q(karar_ozeti__icontains=word) |
                    Q(anahtar_kelimeler__icontains=word) |
                    Q(karar_tam_metni__icontains=word)
                )
            judicial_results = JudicialDecision.objects.filter(q_objects)
            
        if words and area in ['legislation', 'both']:
            q_objects = Q()
            for word in words:
                q_objects &= (
                    Q(baslik__icontains=word) |
                    Q(konu__icontains=word)
                )
            legislation_results = Legislation.objects.filter(q_objects)
            
        if words and area in ['articles', 'both']:
            q_objects = Q()
            for word in words:
                q_objects &= (
                    Q(makale_basligi__icontains=word) |
                    Q(makale_ozeti__icontains=word) |
                    Q(makale_metni__icontains=word)
                )
            article_results = Article.objects.filter(q_objects)

    context = {
        'query': query,
        'area': area,
        'judicial_results': judicial_results,
        'legislation_results': legislation_results,
        'article_results': article_results,
    }
    return render(request, 'core/combined_search_results.html', context)
EOF < /dev/null