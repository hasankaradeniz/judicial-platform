# Türk Ticaret Kanunu (6102) Ekleme Script'i
# Django shell ile çalıştırılacak

from core.models import LegislationType, LegislationCategory, ProfessionalLegislation, LegislationArticle
from datetime import date

# TTK için temel bilgiler
ttk_data = {
    'title': 'Türk Ticaret Kanunu',
    'number': '6102',
    'legislation_type': LegislationType.objects.get(code='kanun'),
    'category': LegislationCategory.objects.get(code='ticaret'),
    'official_gazette_date': date(2011, 2, 14),
    'official_gazette_number': '27846',
    'effective_date': date(2012, 7, 1),
    'publication_date': date(2011, 1, 13),
    'acceptance_date': date(2011, 1, 13),
    'status': 'active',
    'subject': 'Ticari işletmeler, şirketler, ticari senetler, sigorta hukuku ve deniz ticareti',
    'summary': '6102 sayılı Türk Ticaret Kanunu, ticari hayatın temel kurallarını düzenleyen ana kanundur. Ticari işletme, şirketler hukuku, ticari senetler, sigorta ve deniz ticareti konularını kapsar.',
    'keywords': 'ticaret, şirket, ticari işletme, ticari senet, sigorta, deniz ticareti, limited şirket, anonim şirket',
    'mevzuat_gov_id': '6102',
    'source_url': 'https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=6102',
    'pdf_url': 'https://www.mevzuat.gov.tr/MevzuatMetin/1.5.6102.pdf'
}

# TTK'yı oluştur
ttk, created = ProfessionalLegislation.objects.get_or_create(
    number='6102',
    defaults=ttk_data
)

if created:
    print("✅ Türk Ticaret Kanunu (6102) eklendi!")
else:
    print("⚠️ Türk Ticaret Kanunu zaten mevcut")

# Temel maddeler
ttk_articles = [
    {
        'article_number': '1',
        'title': 'Ticari işletme',
        'text': '''Bir ticari işletme işleten kişi tacirdir.

Ticari işletme, ticari faaliyetin devamlı ve bağımsız şekilde yürütüldüğü işletmedir.

Ticari faaliyet; ticari iş yapma, emtia veya hizmet üretme, satma veya pazarlama faaliyetleridir.''',
        'order': 1
    },
    {
        'article_number': '2',
        'title': 'Küçük esnaf',
        'text': '''Ticari faaliyeti küçük çapta olan ve bu Kanunun 18 inci maddesinde öngörülen defter tutma yükümlülüğü bulunmayan kişiler küçük esnaftır ve tacir sayılmazlar.

Ancak, küçük esnaf da, tacirler gibi ticari teamüllere tabidir.''',
        'order': 2
    },
    {
        'article_number': '3',
        'title': 'Tacir yardımcıları',
        'text': '''Tacir yardımcıları, işletme sahibi ile aralarında hizmet ilişkisi bulunan ve işletmenin faaliyetlerine katılan kişilerdir.

Tacir yardımcıları, bağımlı ve bağımsız tacir yardımcıları olarak ikiye ayrılır.''',
        'order': 3
    },
    {
        'article_number': '11',
        'title': 'Ticaret unvanı',
        'text': '''Gerçek kişi tacirin ticaret unvanı, ad ve soyadından oluşur. 

Ticaret unvanına, faaliyet konusunu belirten ve ayırt edici nitelikte ibareler eklenebilir.

Ticaret unvanı, kişiye sıkı surette bağlıdır. Devir ve miras yoluyla geçmez.''',
        'order': 4
    },
    {
        'article_number': '18',
        'title': 'Defter tutma yükümlülüğü',
        'text': '''Tacir, ticari işletmesinin durumunu ve işlemlerini gösteren defterler tutar ve belgeler düzenler veya muhafaza eder.

Defter tutma yükümlülüğünün kapsamı ve usulü yönetmelikle belirlenir.''',
        'order': 5
    },
    {
        'article_number': '124',
        'title': 'Şirket türleri',
        'text': '''Bu Kanuna göre şirketler:
a) Şahıs şirketleri:
   1) Kollektif şirket,
   2) Komandit şirket,
b) Sermaye şirketleri:
   1) Anonim şirket,
   2) Limited şirket,
   3) Sermayesi paylara bölünmüş komandit şirket,
olmak üzere beş türdür.

Kooperatif şirketler özel kanunlarına tabidir.''',
        'order': 6
    },
    {
        'article_number': '125',
        'title': 'Tüzel kişilik',
        'text': '''Şirketler, tescil ile tüzel kişilik kazanırlar.

Şirket sözleşmelerinin ticaret sicili müdürlüğünce tescil edilebilmesi için verilecek belgelerin belirlenmesine, şirket kuruluşlarıyla ilgili işlemlere ve bu işlemlere uygulanacak tarifeye ilişkin usul ve esaslar yönetmelikle düzenlenir.''',
        'order': 7
    },
    {
        'article_number': '329',
        'title': 'Tanım',
        'text': '''Anonim şirket, sermayesi belirli ve paylara bölünmüş olan ve ortakların borçlardan sorumluluğu, taahhüt etikleri sermaye miktarıyla sınırlı bulunan şirkettir.''',
        'order': 8
    },
    {
        'article_number': '573',
        'title': 'Limited şirket tanımı',
        'text': '''Limited şirket; sermayesi belirli ve esas sermaye paylarına bölünmüş olan, ortakların sorumluluğu taahhüt ettikleri sermaye payları ile sınırlı bulunan şirkettir.

Ortaklar esas sözleşmede öngörülmedikce şirkete karşı ek ödeme yükümlülüğü altına girmezler.''',
        'order': 9
    },
    {
        'article_number': '1530',
        'title': 'Yürürlük',
        'text': '''Bu Kanun 1/7/2012 tarihinde yürürlüğe girer.

Ancak;
a) Ticaret sicili, ticaret unvanı ve işletme adına ilişkin hükümler 1/10/2011 tarihinde,
b) Şirketlerin kuruluş ve sona ermesine ilişkin hükümler ile limited şirket ortaklarının oy haklarının devrine ilişkin 595 inci madde hükümleri 1/2/2012 tarihinde,
yürürlüğe girer.''',
        'order': 10
    }
]

# Maddeleri ekle
for article_data in ttk_articles:
    article, created = LegislationArticle.objects.get_or_create(
        legislation=ttk,
        article_number=article_data['article_number'],
        defaults=article_data
    )
    
    if created:
        print(f"✅ Madde {article.article_number}: {article.title} eklendi")
    else:
        print(f"⚠️ Madde {article.article_number} zaten mevcut")

print(f"\n🎉 TTK toplam {ttk.articles.count()} madde ile hazır!")
print(f"📊 URL: /legislation/{ttk.slug}/")
print(f"🔗 Mevzuat ID: {ttk.mevzuat_gov_id}")