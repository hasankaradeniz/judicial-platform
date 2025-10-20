# Türk Borçlar Kanunu (6098) Ekleme Script'i

from core.models import LegislationType, LegislationCategory, ProfessionalLegislation, LegislationArticle
from datetime import date

# TBK için temel bilgiler
tbk_data = {
    'title': 'Türk Borçlar Kanunu',
    'number': '6098',
    'legislation_type': LegislationType.objects.get(code='kanun'),
    'category': LegislationCategory.objects.get(code='borclar'),
    'official_gazette_date': date(2011, 2, 4),
    'official_gazette_number': '27836',
    'effective_date': date(2012, 7, 1),
    'publication_date': date(2011, 1, 11),
    'acceptance_date': date(2011, 1, 11),
    'status': 'active',
    'subject': 'Sözleşmeler, haksız fiiller, sebepsiz zenginleşme ve borç ilişkileri',
    'summary': '6098 sayılı Türk Borçlar Kanunu, borç ilişkilerinin genel esaslarını, sözleşmeleri, haksız fiilleri ve sebepsiz zenginleşmeyi düzenler.',
    'keywords': 'borç, sözleşme, haksız fiil, sebepsiz zenginleşme, tazminat, ifa, akdi sorumluluk',
    'mevzuat_gov_id': '6098',
    'source_url': 'https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=6098',
    'pdf_url': 'https://www.mevzuat.gov.tr/MevzuatMetin/1.5.6098.pdf'
}

# TBK'yı oluştur
tbk, created = ProfessionalLegislation.objects.get_or_create(
    number='6098',
    defaults=tbk_data
)

if created:
    print("✅ Türk Borçlar Kanunu (6098) eklendi!")
else:
    print("⚠️ Türk Borçlar Kanunu zaten mevcut")

# Temel maddeler
tbk_articles = [
    {
        'article_number': '1',
        'title': 'Sözleşme kurulması',
        'text': '''Sözleşme, karşılıklı ve birbirine uygun irade beyanlarıyla kurulur.

İrade beyanının şekli kanunda öngörülmedikçe serbesttir.''',
        'order': 1
    },
    {
        'article_number': '2',
        'title': 'Önceden hazırlanmış sözleşme koşulları',
        'text': '''Önceden hazırlanmış sözleşme koşulları, ancak karşı tarafın gerçek anlamda bunları öğrenme imkânı bulmuş olması hâlinde sözleşmenin kapsamına girer.

Bu koşullardan açık olmayan bir hüküm, onu kullanan aleyhine yorumlanır.''',
        'order': 2
    },
    {
        'article_number': '26',
        'title': 'Genel olarak ifa',
        'text': '''Borçlu, borcunu özenle ve sadakat kurallarına uygun olarak ifa etmek zorundadır.

İfa, borçlunun kişisel çalışmasını gerektirmediği takdirde, üçüncü bir kişi tarafından da yapılabilir.''',
        'order': 3
    },
    {
        'article_number': '49',
        'title': 'Haksız fiilden doğan sorumluluk',
        'text': '''Kusurlu ve hukuka aykırı bir fiille başkasına zarar veren, bu zararı gidermekle yükümlüdür.

Zarar verici fiili yapmakta ayırt etme gücünden yoksun bulunan kimse, zarardan sorumlu değildir.''',
        'order': 4
    },
    {
        'article_number': '50',
        'title': 'Zarar türleri',
        'text': '''Zarar, malvarlığında meydana gelen eksilmeyi (pozitif zarar), malvarlığında meydana gelmesi olağan olan artışın gerçekleşmemesini (yoksun kalınan kâr) ve manevi zararı kapsar.''',
        'order': 5
    },
    {
        'article_number': '60',
        'title': 'Kusursuz sorumluluk halleri',
        'text': '''Kendisine ait binalar veya diğer yapıtlardan doğan tehlike dolayısıyla başkalarına zarar veren kimse, zarar verme kastı olmadığını ve gereken özeni gösterdiğini ispat etmedikçe, bu zararı gidermekle yükümlüdür.''',
        'order': 6
    },
    {
        'article_number': '77',
        'title': 'Tazminatın belirlenmesi',
        'text': '''Zarar gören, uğradığı zararın giderilmesini isteyebilir.

Zararın aynı şekilde giderilmesi mümkün değilse veya bu yeterli bir giderim sayılmazsa, zarar para ile tazmin edilir.''',
        'order': 7
    },
    {
        'article_number': '417',
        'title': 'Satım sözleşmesinin tanımı',
        'text': '''Satım sözleşmesi, satıcının bir malı alıcıya teslim etmeyi ve o malın mülkiyetini alıcıya geçirmeyi, alıcının ise semenini ödemeyi üstlendiği sözleşmedir.''',
        'order': 8
    },
    {
        'article_number': '470',
        'title': 'Kira sözleşmesinin tanımı',
        'text': '''Kira sözleşmesi, kiraya verenin kiracıya bir şeyin kullanılmasını bırakmayı, kiracının da bunun karşılığında kira bedeli ödemeyi üstlendiği sözleşmedir.''',
        'order': 9
    },
    {
        'article_number': '647',
        'title': 'Yürürlük',
        'text': '''Bu Kanun 1/7/2012 tarihinde yürürlüğe girer.

Ancak, taşıma sözleşmelerine ilişkin hükümler 1/6/2013 tarihinde yürürlüğe girer.''',
        'order': 10
    }
]

# Maddeleri ekle
for article_data in tbk_articles:
    article, created = LegislationArticle.objects.get_or_create(
        legislation=tbk,
        article_number=article_data['article_number'],
        defaults=article_data
    )
    
    if created:
        print(f"✅ Madde {article.article_number}: {article.title} eklendi")
    else:
        print(f"⚠️ Madde {article.article_number} zaten mevcut")

print(f"\n🎉 TBK toplam {tbk.articles.count()} madde ile hazır!")
print(f"📊 URL: /legislation/{tbk.slug}/")
print(f"🔗 Mevzuat ID: {tbk.mevzuat_gov_id}")