# Toplu mevzuat ekleme script'i - TMK, İİK, TCK

from core.models import LegislationType, LegislationCategory, ProfessionalLegislation, LegislationArticle
from datetime import date

# Kanun türü ve kategorileri al
kanun_turu = LegislationType.objects.get(code='kanun')
medeni_kategori = LegislationCategory.objects.get(code='medeni')
ceza_kategori = LegislationCategory.objects.get(code='ceza')

# TÜRK MEDENİ KANUNU (4721)
tmk_data = {
    'title': 'Türk Medeni Kanunu',
    'number': '4721',
    'legislation_type': kanun_turu,
    'category': medeni_kategori,
    'official_gazette_date': date(2001, 12, 8),
    'official_gazette_number': '24607',
    'effective_date': date(2002, 1, 1),
    'publication_date': date(2001, 11, 22),
    'acceptance_date': date(2001, 11, 22),
    'status': 'active',
    'subject': 'Kişi hukuku, aile hukuku, miras hukuku, eşya hukuku',
    'summary': '4721 sayılı Türk Medeni Kanunu, kişi hakları, aile hukuku, miras hukuku ve eşya hukukunu düzenleyen temel kanundur.',
    'keywords': 'medeni, kişi hakları, aile, evlilik, miras, mülkiyet, tapu',
    'mevzuat_gov_id': '4721',
    'source_url': 'https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=4721',
    'pdf_url': 'https://www.mevzuat.gov.tr/MevzuatMetin/1.5.4721.pdf'
}

tmk, created = ProfessionalLegislation.objects.get_or_create(number='4721', defaults=tmk_data)
if created: print("✅ Türk Medeni Kanunu (4721) eklendi!")

# İCRA VE İFLAS KANUNU (2004)
iik_data = {
    'title': 'İcra ve İflas Kanunu',
    'number': '2004',
    'legislation_type': kanun_turu,
    'category': medeni_kategori,  # Usul hukuku kategorisi yoksa medeni altına
    'official_gazette_date': date(1932, 6, 19),
    'official_gazette_number': '2128',
    'effective_date': date(1932, 10, 1),
    'status': 'active',
    'subject': 'İcra takibi, haciz, iflas, konkordato',
    'summary': '2004 sayılı İcra ve İflas Kanunu, alacaklıların haklarını zorla elde etme usullerini düzenler.',
    'keywords': 'icra, iflas, haciz, konkordato, alacak, borç',
    'mevzuat_gov_id': '2004',
    'source_url': 'https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=2004',
    'pdf_url': 'https://www.mevzuat.gov.tr/MevzuatMetin/1.5.2004.pdf'
}

iik, created = ProfessionalLegislation.objects.get_or_create(number='2004', defaults=iik_data)
if created: print("✅ İcra ve İflas Kanunu (2004) eklendi!")

# TÜRK CEZA KANUNU (5237)
tck_data = {
    'title': 'Türk Ceza Kanunu',
    'number': '5237',
    'legislation_type': kanun_turu,
    'category': ceza_kategori,
    'official_gazette_date': date(2004, 10, 12),
    'official_gazette_number': '25611',
    'effective_date': date(2005, 6, 1),
    'publication_date': date(2004, 9, 26),
    'acceptance_date': date(2004, 9, 26),
    'status': 'active',
    'subject': 'Suçlar, cezalar, güvenlik tedbirleri',
    'summary': '5237 sayılı Türk Ceza Kanunu, suçları ve bunlara verilecek cezaları düzenleyen temel kanundur.',
    'keywords': 'ceza, suç, hapis, para cezası, güvenlik tedbiri',
    'mevzuat_gov_id': '5237',
    'source_url': 'https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=5237',
    'pdf_url': 'https://www.mevzuat.gov.tr/MevzuatMetin/1.5.5237.pdf'
}

tck, created = ProfessionalLegislation.objects.get_or_create(number='5237', defaults=tck_data)
if created: print("✅ Türk Ceza Kanunu (5237) eklendi!")

# TMK Temel Maddeleri
tmk_articles = [
    {'article_number': '1', 'title': 'Kanunun uygulanması', 'text': 'Kanun, lafzı veya ruhu ile bir olaya uygulanabilen her durumda hâkim tarafından uygulanır.', 'order': 1},
    {'article_number': '8', 'title': 'Kişilik', 'text': 'Her insanın hak ehliyeti vardır. Buna göre bütün insanlar, hukuk düzeni içinde, haklara ve borçlara ehil olmakta eşittirler.', 'order': 2},
    {'article_number': '28', 'title': 'Kişilik haklarının korunması', 'text': 'Kişilik hakkına saldırıda bulunan kimseye karşı, hâkimden saldırının men\'ini isteyebilir; saldırı zararla sonuçlanmışsa tazminat isteyebilir.', 'order': 3},
    {'article_number': '134', 'title': 'Evlenme yaşı', 'text': 'Erkek ve kadın on sekiz yaşını doldurmuş olmadıkça evlenemezler.', 'order': 4},
    {'article_number': '185', 'title': 'Boşanma sebepleri', 'text': 'Eşlerden her biri evlilik birliğinin temelinden sarsılması sebebiyle boşanma davası açabilir.', 'order': 5}
]

# İİK Temel Maddeleri  
iik_articles = [
    {'article_number': '1', 'title': 'İcra dairelerinin görevleri', 'text': 'İcra daireleri, kanuni şartlara uygun olarak kendilerine ibraz olunan belgelere dayanarak icra takibi yaparlar.', 'order': 1},
    {'article_number': '58', 'title': 'İcra takibine başlama', 'text': 'İcra takibi, alacaklının veya vekilinin icra dairesine vereceği bir dilekçe ile başlar.', 'order': 2},
    {'article_number': '179', 'title': 'İflas sebepleri', 'text': 'Ticari işletmesini durduran veya durdurmak zorunda kalan tacir, iflas eder.', 'order': 3}
]

# TCK Temel Maddeleri
tck_articles = [
    {'article_number': '1', 'title': 'Amaç', 'text': 'Bu Kanunun amacı; kişi haklarını, kamu düzen ve güvenliğini korumaktır.', 'order': 1},
    {'article_number': '20', 'title': 'Kast', 'text': 'Suçun oluşması kastın varlığına bağlıdır. Kast, suçun kanuni tanımındaki unsurların bilinmesi ve istenmesidir.', 'order': 2},
    {'article_number': '81', 'title': 'Kasten öldürme', 'text': 'Kasten bir insanı öldüren kişi, ömür boyu hapis cezası ile cezalandırılır.', 'order': 3}
]

# Maddeleri ekle
for legislation, articles in [(tmk, tmk_articles), (iik, iik_articles), (tck, tck_articles)]:
    for article_data in articles:
        article_data['legislation'] = legislation
        article, created = LegislationArticle.objects.get_or_create(
            legislation=legislation,
            article_number=article_data['article_number'],
            defaults=article_data
        )
        if created:
            print(f"✅ {legislation.number} - Madde {article.article_number}: {article.title}")

print(f"\n🎉 5 TEMEL KANUN TAMAMLANDI!")
print(f"📊 TTK: {ProfessionalLegislation.objects.get(number='6102').articles.count()} madde")
print(f"📊 TBK: {ProfessionalLegislation.objects.get(number='6098').articles.count()} madde") 
print(f"📊 TMK: {ProfessionalLegislation.objects.get(number='4721').articles.count()} madde")
print(f"📊 İİK: {ProfessionalLegislation.objects.get(number='2004').articles.count()} madde")
print(f"📊 TCK: {ProfessionalLegislation.objects.get(number='5237').articles.count()} madde")
print(f"\n✅ Toplam: {ProfessionalLegislation.objects.count()} kanun hazır!")