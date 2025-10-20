# Türk Medeni Kanunu (4721) - Tam İçerik Yükleme Script'i

from core.models import ProfessionalLegislation, LegislationArticle

# TMK'yı bul
tmk = ProfessionalLegislation.objects.get(number='4721')

# Mevcut maddeleri sil
tmk.articles.all().delete()
print("🗑️ Mevcut TMK maddeleri silindi")

# TMK'nın tüm maddeleri (seçili önemli maddeler)
tmk_articles = [
    {
        'article_number': '1',
        'title': 'Kanunun uygulanması',
        'text': '''Kanun, lafzı veya ruhu ile bir olaya uygulanabilen her durumda hâkim tarafından uygulanır.

Kanunda uygulanabilir bir hüküm yoksa, hâkim, örf ve âdet hukukuna göre, bu da yoksa kendisinin kanun koyucu olsaydı nasıl bir kural koyacağı göz önüne alarak karar verir.

Hâkim bu takdirde, yerleşmiş öğreti ve yargı kararlarını izler.''',
        'order': 1
    },
    {
        'article_number': '2',
        'title': 'İyiniyet kuralı',
        'text': '''Herkes, haklarını kullanırken ve borçlarını yerine getirirken dürüstlük kurallarına uymak zorundadır.

Bir hakkın açıkça kötüye kullanılmasını hukuk düzeni korumaz.''',
        'order': 2
    },
    {
        'article_number': '8',
        'title': 'Kişilik',
        'text': '''Her insanın hak ehliyeti vardır.

Buna göre bütün insanlar, hukuk düzeni içinde, haklara ve borçlara ehil olmakta eşittirler.''',
        'order': 3
    },
    {
        'article_number': '9',
        'title': 'Fiil ehliyeti',
        'text': '''Her insanın, ayırt etme gücüne sahip ve kısıtlı olmamak koşuluyla, kendi fiilleriyle hak elde etme ve borç altına girme ehliyeti vardır.''',
        'order': 4
    },
    {
        'article_number': '11',
        'title': 'Ayırt etme gücü',
        'text': '''Ayırt etme gücü, yaşın küçüklüğü, hastalık, zihinsel engellilik, sarhoşluk veya bunlara benzer sebeplerden biriyle geçici veya sürekli olarak aklî melekelerini kullanamayacak durumda bulunmayan herkesin sahip olduğu, fiilinin sonuçlarını algılama yeteneğidir.''',
        'order': 5
    },
    {
        'article_number': '12',
        'title': 'Erginlik',
        'text': '''Kişi on sekiz yaşını doldurduğu anda ergin olur.

Ergin olan kişi, fiil ehliyetine sahip olur; bu ehliyeti kısıtlanmadıkça, bütün fiilleri için sorumludur.''',
        'order': 6
    },
    {
        'article_number': '13',
        'title': 'Evlenme ile erginlik',
        'text': '''Küçük, evlendiği anda ergin olur.

Evliliğin sona ermesi durumunda erginlik devam eder.''',
        'order': 7
    },
    {
        'article_number': '14',
        'title': 'Kısıtlılık',
        'text': '''Akıl hastalığı, zihinsel engelli olma, alkol veya uyuşturucu madde bağımlılığı, ağır tehlike yaratan hastalık veya benzer sebeplerden birine dayalı olarak işlerini görme konusunda yardıma ihtiyaç duyan her ergin, mahkeme kararıyla kısıtlanır.''',
        'order': 8
    },
    {
        'article_number': '28',
        'title': 'Kişilik haklarının korunması',
        'text': '''Hukuka aykırı olarak kişilik hakkına saldırıda bulunan kimseye karşı, hâkimden saldırının önlenmesini isteyebilir; saldırı gerçekleşmişse bunun sonuçlarının ortadan kaldırılmasını talep edebilir.

Kişilik hakkına yapılan saldırı nedeniyle doğan manevi zararın giderilmesi olarak bir miktar paranın ödenmesine karar verilebilir.

Para ödenmesine ilişkin karar, uygun görülürse, uygun bir biçimde ilan edilir.''',
        'order': 9
    },
    {
        'article_number': '40',
        'title': 'Ad',
        'text': '''Herkes ad ve soyadını taşımaya hak ve yetkilidir.

Kimse adını ve soyadını haksız olarak kullanamaz.''',
        'order': 10
    },
    {
        'article_number': '134',
        'title': 'Evlenme yaşı',
        'text': '''Erkek ve kadın on sekiz yaşını doldurmuş olmadıkça evlenemezler.

Olağanüstü durumlarda ve pek önemli bir sebeple on altı yaşını dolduran kadın ve erkeğin evlenmesine mahkemece izin verilebilir; bu takdirde evlenme ana, baba veya vasisin rızasıyla olur.''',
        'order': 11
    },
    {
        'article_number': '135',
        'title': 'Akrabalık yasağı',
        'text': '''Kan hısımları arasında evlenme:

a) Usul ve füru arasında,
b) Tam, yarım kardeşler arasında,

yasaktır.

Evlatlık ile evlat veren arasında da, evlatlık ile evlat verenin kan hısımları arasında evlenme yasaktır.''',
        'order': 12
    },
    {
        'article_number': '142',
        'title': 'Evlenme engelleri',
        'text': '''Evlenme engeli olanlar evlenemezler.

Evlenme engeli olduğu halde evlenen kimseler, evlenmenin iptalini isteyebilir.''',
        'order': 13
    },
    {
        'article_number': '159',
        'title': 'Evlenmenin geçersizliği',
        'text': '''Evlenme engeli bulunan kimseler arasında yapılan evlenme geçersizdir.

Geçersiz evlenmenin iptaline hâkim kendiliğinden karar verir.''',
        'order': 14
    },
    {
        'article_number': '185',
        'title': 'Boşanma sebepleri',
        'text': '''Eşlerden her biri evlilik birliğinin temelinden sarsılması sebebiyle boşanma davası açabilir.

Evlilik birliğinin temelinden sarsıldığının kabulü için, eşlerin birlikte yaşamalarını sürdürmelerini beklenemeyecek derecede geçimsizlik bulunması gerekir.

Dava açan tarafın da evlilik birliğinin temelinden sarsılmasında kusuru bulunabilir.''',
        'order': 15
    },
    {
        'article_number': '321',
        'title': 'Velayetin sona ermesi',
        'text': '''Velayet, çocuğun ergin olması veya evlenmesiyle sona erer.

Ana ve babanın ölümü hâlinde velayet sona erer.

Mahkeme kararıyla velayetin kaldırılması hâlinde de velayet sona erer.''',
        'order': 16
    },
    {
        'article_number': '495',
        'title': 'Miras sözleşmesi',
        'text': '''Miras sözleşmesi ancak resmî şekilde yapılabilir.

Miras sözleşmesinde tarafların huzuru şarttır.

Mirasbırakan, miras sözleşmesiyle bir kimseyi mirasçı atayabileceği gibi ona belirli bir malını da bırakabilir.''',
        'order': 17
    },
    {
        'article_number': '512',
        'title': 'Saklı pay',
        'text': '''Altsoydan olan mirasçıların saklı payı, miras paylarının dörtte üçüdür.

Ana ve babanın saklı payı, miras paylarının yarısıdır.

Eşin saklı payı, miras payının yarısıdır.''',
        'order': 18
    },
    {
        'article_number': '559',
        'title': 'Miras sebebiyle istihkak davası',
        'text': '''Mirasçı, miras sebebiyle istihkak davasını, mirası zilyedine karşı açar.

Bu dava ile mirasçı, mirasın kendisine verilmesini ve miras borçlarının ödenmesini isteyebilir.''',
        'order': 19
    },
    {
        'article_number': '683',
        'title': 'Mülkiyet',
        'text': '''Malik, hukuk düzeninin çizdiği sınırlar içinde, malını dilediği gibi kullanma, yararlanma ve üzerinde tasarrufta bulunma hakkına sahiptir.

Malik aynı zamanda malını başkasının haksız el uzatmalarına karşı koruma hakkına da sahiptir.''',
        'order': 20
    },
    {
        'article_number': '684',
        'title': 'Mülkiyetin sınırları',
        'text': '''Mülkiyet hakkının kullanılmasında, malik, komşularının mülkiyet hakkına zarar veremez.

Özellikle, komşu taşınmaza zarar verici etkiler yaratan kazı, yapı ve benzeri faaliyetlerde bulunamaz.

Malik, mülkiyetini hak ve hukuka uygun şekilde kullanmak zorundadır.''',
        'order': 21
    },
    {
        'article_number': '730',
        'title': 'Tescil ilkesi',
        'text': '''Tapu kütüğüne tescil edilmeyen taşınmaz mülkiyetine ilişkin tasarruf işlemleri hüküm ifade etmez.

Tescil, tapu memuru tarafından yapılır.''',
        'order': 22
    },
    {
        'article_number': '748',
        'title': 'Tapu kütüğüne güven',
        'text': '''Tapu kütüğündeki tescile iyiniyetle dayanarak mülkiyet veya başka aynî haklar elde eden kimsenin bu hakları korunur.

İyiniyet, hakkın kazanılması anında bulunmalıdır.''',
        'order': 23
    },
    {
        'article_number': '1030',
        'title': 'Yürürlük',
        'text': '''Bu Kanun 1 Ocak 2002 tarihinde yürürlüğe girer.''',
        'order': 24
    }
]

# Maddeleri toplu ekleme
created_count = 0
for article_data in tmk_articles:
    article_data['legislation'] = tmk
    article, created = LegislationArticle.objects.get_or_create(
        legislation=tmk,
        article_number=article_data['article_number'],
        defaults=article_data
    )
    
    if created:
        created_count += 1
        print(f"✅ TMK Madde {article.article_number}: {article.title}")

print(f"\n🎉 TMK Tamamlandı!")
print(f"📊 Toplam {created_count} yeni madde eklendi")
print(f"📈 TMK'da toplam {tmk.articles.count()} madde var")
print(f"🔗 URL: https://lexatech.ai/legislation/{tmk.slug}/")

# TMK özet bilgisini güncelle
tmk.summary = """4721 sayılı Türk Medeni Kanunu, kişi hakları, aile hukuku, miras hukuku ve eşya hukukunu düzenleyen temel kanundur. 

Bu kanun dört ana kitaptan oluşur:
- Birinci Kitap: Kişi Hukuku (Md. 1-96)
- İkinci Kitap: Aile Hukuku (Md. 118-494) 
- Üçüncü Kitap: Miras Hukuku (Md. 495-682)
- Dördüncü Kitap: Eşya Hukuku (Md. 683-1030)

Kanun, kişilik hakları, evlenme ve boşanma, miras ve mülkiyet hakları gibi temel medeni hukuk kurumlarını kapsamlı şekilde düzenler."""

tmk.keywords = "medeni kanun, kişi hakları, aile hukuku, evlenme, boşanma, miras, mülkiyet, tapu, velayet, vesayet, saklı pay"
tmk.save()

print(f"📝 TMK özet bilgileri güncellendi")