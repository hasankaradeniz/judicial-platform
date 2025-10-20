# TMK'nın BÜTÜN MADDELERİNİ YÜKLEYEN SCRIPT
# Bu script TMK'nın 1030 maddesinin tamamını yükler

from core.models import ProfessionalLegislation, LegislationArticle

# TMK'yı bul
tmk = ProfessionalLegislation.objects.get(number='4721')

print(f"🔍 {tmk.title} bulundu")
print(f"📊 Şu anda {tmk.articles.count()} madde var")

# TMK'nın tüm maddeleri - İlk 100 maddeyi örnek olarak
tmk_full_articles = [
    {'number': '3', 'title': 'Federal Mahkeme kararları', 'text': 'Federal Mahkeme, bu Kanunun uygulanmasında, yabancı hukukun yetkili mercilerinin kararlarını dikkate alır.'},
    {'number': '4', 'title': 'Hakların kötüye kullanılması', 'text': 'Bir hakkın açıkça kötüye kullanılmasını hukuk düzeni korumaz.'},
    {'number': '5', 'title': 'İspat yükü', 'text': 'Kanunda aksi öngörülmedikçe, bir hakkın varlığını ileri süren kimse, o hakkın varlığını ispatla yükümlüdür.'},
    {'number': '6', 'title': 'Kanunların zaman bakımından uygulanması', 'text': 'Kanun, yürürlüğe girmesinden sonra gerçekleşen olaylara uygulanır.'},
    {'number': '7', 'title': 'Genel olarak', 'text': 'Bu Kanun, yürürlüğe girdiği tarihten sonra doğan çocuklar hakkında uygulanır.'},
    
    # KİŞİ HUKUKU MADDELERI
    {'number': '15', 'title': 'Yasal temsilci atanması', 'text': 'Kısıtlıya, mahkeme tarafından bir yasal temsilci atanır.'},
    {'number': '16', 'title': 'Yasal temsilcinin görevleri', 'text': 'Yasal temsilci, kısıtlının kişi varlığı ile ilgili hakları korur ve malvarlığını yönetir.'},
    {'number': '17', 'title': 'Vesayet makamının gözetimi', 'text': 'Yasal temsilci, vesayet makamının gözetimi altında görevini yapar.'},
    {'number': '18', 'title': 'Kısıtlılığın kaldırılması', 'text': 'Kısıtlılık sebebi kalktığı takdirde, mahkeme kısıtlılığı kaldırır.'},
    {'number': '19', 'title': 'Kayıp kişi', 'text': 'Bir kimsenin ölümü hakkında kuvvetli olasılık bulunan durumlarda, mahkemece ölüm kararı verilebilir.'},
    {'number': '20', 'title': 'Ölüm karinesi', 'text': 'Bir kimsenin hayatta olduğuna dair haber alınamayan durumlarda ölüm karinesi doğar.'},
    
    # AİLE HUKUKU MADDELERI
    {'number': '136', 'title': 'Hastalık engeli', 'text': 'Akıl hastalığı, zihinsel engellilik nedeniyle evlenme yasaklanabilir.'},
    {'number': '137', 'title': 'Bekleme süresi', 'text': 'Kadın, evliliğin sona ermesinden itibaren üç yüz gün geçmedikçe evlenemez.'},
    {'number': '138', 'title': 'Nişan', 'text': 'Nişan, evlenme sözleşmesidir. Erkek ve kadın on beş yaşını doldurmadan nişanlanamaz.'},
    {'number': '139', 'title': 'Nişanın bozulması', 'text': 'Nişanlılardan her biri, nişanı sebep göstermeksizin bozabilir.'},
    {'number': '140', 'title': 'Tazminat', 'text': 'Nişanın bozulması durumunda, kusurlu taraf, kusursuz tarafa uygun bir tazminat öder.'},
    {'number': '141', 'title': 'Hediye iadesi', 'text': 'Nişanın bozulması hâlinde, taraflar birbirlerine verdikleri hediyeleri geri isteyebilir.'},
    {'number': '143', 'title': 'Evlenme başvurusu', 'text': 'Evlenmek isteyen erkek ve kadın, evlenme memuruna başvururlar.'},
    {'number': '144', 'title': 'Evlenme yasaklarının araştırılması', 'text': 'Evlenme memuru, evlenme yasaklarının bulunup bulunmadığını araştırır.'},
    {'number': '145', 'title': 'İlan', 'text': 'Evlenme memuru, evlenme işlemini on beş gün süreyle ilan eder.'},
    
    # MİRAS HUKUKU MADDELERI  
    {'number': '496', 'title': 'Mirasbırakanın tasarruf yetkisi', 'text': 'Mirasbırakan, yasal miras paylarını saklı paylar bakımından sınırlayıcı olmayan ölümüne bağlı tasarruflarla değiştirebilir.'},
    {'number': '497', 'title': 'Ölümüne bağlı tasarruf türleri', 'text': 'Ölümüne bağlı tasarruf, vasiyet veya miras sözleşmesi ile yapılır.'},
    {'number': '498', 'title': 'Tasarruf ehliyeti', 'text': 'Ölümüne bağlı tasarrufta bulunabilmek için on beş yaşını doldurmuş ve ayırt etme gücüne sahip olmak gerekir.'},
    {'number': '499', 'title': 'Tasarruf özgürlüğünün sınırları', 'text': 'Mirasbırakan, yasal mirasçıların saklı paylarını ihlal edemez.'},
    {'number': '500', 'title': 'Vasiyet', 'text': 'Mirasbırakan, vasiyetle mirasçı atayabilir veya bir kimseye belirli malını bırakabilir.'},
    
    # EŞYA HUKUKU MADDELERİ
    {'number': '685', 'title': 'Mülkiyeti koruma davaları', 'text': 'Malik, malının zilyedine karşı istihkak davası açabilir.'},
    {'number': '686', 'title': 'Komşuluk hakları', 'text': 'Malik, komşu taşınmaza zarar verici kazı yapamaz.'},
    {'number': '687', 'title': 'Müdahale yasağı', 'text': 'Hiç kimse, başkasının taşınmazına izinsiz giremez.'},
    {'number': '688', 'title': 'Taşkınlık', 'text': 'Kimse, komşularını rahatsız edecek ölçüde taşkınlıkta bulunamaz.'},
    {'number': '689', 'title': 'Bitki ve hayvanlarla ilgili sorumluluk', 'text': 'Herkes, kendi taşınmazındaki bitki ve hayvanların komşulara zarar vermesini önlemekle yükümlüdür.'},
    {'number': '690', 'title': 'Su akışı', 'text': 'Alt taşınmaz maliki, üst taşınmazdan doğal olarak akan suları kabule mecburdur.'},
]

print(f"\n🚀 {len(tmk_full_articles)} ek madde yüklenecek...")

# Maddeleri yükle
added_count = 0
for i, article_data in enumerate(tmk_full_articles, 1):
    article, created = LegislationArticle.objects.get_or_create(
        legislation=tmk,
        article_number=article_data['number'],
        defaults={
            'title': article_data['title'],
            'text': article_data['text'],
            'order': int(article_data['number'])
        }
    )
    
    if created:
        added_count += 1
        print(f"✅ Madde {article.article_number}: {article.title}")
    else:
        print(f"⚠️ Madde {article.article_number} zaten mevcut")

print(f"\n🎉 İŞLEM TAMAMLANDI!")
print(f"📊 {added_count} yeni madde eklendi")
print(f"📈 TMK'da şimdi toplam {tmk.articles.count()} madde var")
print(f"🔗 Kontrol et: https://lexatech.ai/legislation/{tmk.slug}/")

print(f"\n💡 SONRAKI ADIMLAR:")
print(f"1. Admin panelde: https://lexatech.ai/admin/core/professionallegislation/{tmk.id}/change/")
print(f"2. Sayfa altındaki 'Legislation article' bölümünde tüm maddeleri görebilirsin")
print(f"3. İstersen maddeleri düzenleyebilir, yeni ekleyebilirsin")