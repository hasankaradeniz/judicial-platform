# Geri kalan 15 temel kanunu toplu ekleme

from core.models import LegislationType, LegislationCategory, ProfessionalLegislation, LegislationArticle
from datetime import date

kanun_turu = LegislationType.objects.get(code='kanun')

# Kategoriler
anayasa_kat = LegislationCategory.objects.get(code='anayasa')
is_kat = LegislationCategory.objects.get(code='is_sosyal') 
vergi_kat = LegislationCategory.objects.get(code='vergi')
ticaret_kat = LegislationCategory.objects.get(code='ticaret')
borclar_kat = LegislationCategory.objects.get(code='borclar')
medeni_kat = LegislationCategory.objects.get(code='medeni')
ceza_kat = LegislationCategory.objects.get(code='ceza')
idare_kat = LegislationCategory.objects.get(code='idare')

# 15 Temel Kanun
laws_data = [
    {
        'title': 'Türkiye Cumhuriyeti Anayasası',
        'number': '2709',
        'category': anayasa_kat,
        'official_gazette_date': date(1982, 11, 9),
        'official_gazette_number': '17863',
        'effective_date': date(1982, 11, 9),
        'subject': 'Devletin temel yapısı, temel haklar ve ödevler',
        'keywords': 'anayasa, temel haklar, devlet yapısı, cumhuriyet'
    },
    {
        'title': 'İş Kanunu',
        'number': '4857',
        'category': is_kat,
        'official_gazette_date': date(2003, 6, 10),
        'official_gazette_number': '25134',
        'effective_date': date(2003, 6, 10),
        'subject': 'İş ilişkileri, iş sözleşmeleri, işçi hakları',
        'keywords': 'iş, işçi, işveren, iş sözleşmesi, çalışma'
    },
    {
        'title': 'Vergi Usul Kanunu',
        'number': '213',
        'category': vergi_kat,
        'official_gazette_date': date(1961, 1, 10),
        'official_gazette_number': '10703',
        'effective_date': date(1961, 1, 10),
        'subject': 'Vergi usul ve esasları, vergi dairesi işlemleri',
        'keywords': 'vergi, vergi usulü, beyanname, tahsilat'
    },
    {
        'title': 'Gelir Vergisi Kanunu',
        'number': '193',
        'category': vergi_kat,
        'official_gazette_date': date(1960, 12, 6),
        'official_gazette_number': '10682',
        'effective_date': date(1961, 1, 1),
        'subject': 'Gelir vergisi, vergiye tabi gelirler',
        'keywords': 'gelir vergisi, ücret, kar, temettü'
    },
    {
        'title': 'Katma Değer Vergisi Kanunu',
        'number': '3065',
        'category': vergi_kat,
        'official_gazette_date': date(1984, 11, 2),
        'official_gazette_number': '18563',
        'effective_date': date(1985, 1, 1),
        'subject': 'Katma değer vergisi, KDV uygulamaları',
        'keywords': 'kdv, katma değer vergisi, fatura'
    },
    {
        'title': 'Sosyal Sigortalar ve Genel Sağlık Sigortası Kanunu',
        'number': '5510',
        'category': is_kat,
        'official_gazette_date': date(2006, 6, 16),
        'official_gazette_number': '26200',
        'effective_date': date(2008, 5, 1),
        'subject': 'Sosyal güvenlik, sağlık sigortası, emeklilik',
        'keywords': 'sgk, sosyal sigorta, sağlık sigortası, emeklilik'
    },
    {
        'title': 'Tüketicinin Korunması Hakkında Kanun',
        'number': '6502',
        'category': borclar_kat,
        'official_gazette_date': date(2013, 11, 28),
        'official_gazette_number': '28835',
        'effective_date': date(2014, 5, 6),
        'subject': 'Tüketici hakları, tüketici korunması',
        'keywords': 'tüketici, tüketici hakları, garanti'
    },
    {
        'title': 'Sermaye Piyasası Kanunu',
        'number': '6362',
        'category': ticaret_kat,
        'official_gazette_date': date(2012, 12, 30),
        'official_gazette_number': '28513',
        'effective_date': date(2013, 12, 30),
        'subject': 'Sermaye piyasası, menkul kıymetler, borsa',
        'keywords': 'sermaye piyasası, borsa, hisse senedi'
    },
    {
        'title': 'Bankacılık Kanunu',
        'number': '5411',
        'category': ticaret_kat,
        'official_gazette_date': date(2005, 11, 1),
        'official_gazette_number': '25983',
        'effective_date': date(2005, 11, 1),
        'subject': 'Bankacılık faaliyetleri, banka kuruluşu',
        'keywords': 'banka, bankacılık, kredi, mevduat'
    },
    {
        'title': '6570 Sayılı Gayrimenkul Kiralama Kanunu',
        'number': '6570',
        'category': borclar_kat,
        'official_gazette_date': date(2014, 7, 3),
        'official_gazette_number': '29044',
        'effective_date': date(2015, 1, 1),
        'subject': 'Konut ve işyeri kiralama',
        'keywords': 'kira, gayrimenkul, konut, işyeri'
    },
    {
        'title': 'Noterlik Kanunu',
        'number': '1512',
        'category': medeni_kat,
        'official_gazette_date': date(1972, 7, 5),
        'official_gazette_number': '14223',
        'effective_date': date(1972, 10, 1),
        'subject': 'Noterlık, noter işlemleri',
        'keywords': 'noter, noterlik, tasdik, sözleşme'
    },
    {
        'title': 'Avukatlık Kanunu',
        'number': '1136',
        'category': medeni_kat,
        'official_gazette_date': date(1969, 3, 19),
        'official_gazette_number': '13168',
        'effective_date': date(1969, 4, 2),
        'subject': 'Avukatlık mesleği, baro',
        'keywords': 'avukat, avukatlık, baro, dava vekili'
    },
    {
        'title': 'Hukuk Muhakemeleri Kanunu',
        'number': '6100',
        'category': medeni_kat,
        'official_gazette_date': date(2011, 2, 4),
        'official_gazette_number': '27836',
        'effective_date': date(2011, 10, 1),
        'subject': 'Medeni usul hukuku, dava açma, yargılama',
        'keywords': 'dava, mahkeme, yargılama, usul'
    },
    {
        'title': 'Ceza Muhakemesi Kanunu',
        'number': '5271',
        'category': ceza_kat,
        'official_gazette_date': date(2004, 12, 17),
        'official_gazette_number': '25673',
        'effective_date': date(2005, 6, 1),
        'subject': 'Ceza davası usulü, soruşturma, kovuşturma',
        'keywords': 'ceza davası, savcılık, soruşturma, kovuşturma'
    },
    {
        'title': 'İdari Yargılama Usulü Kanunu',
        'number': '2577',
        'category': idare_kat,
        'official_gazette_date': date(1982, 1, 20),
        'official_gazette_number': '17580',
        'effective_date': date(1982, 9, 20),
        'subject': 'İdari yargı, idari dava usulü',
        'keywords': 'idari yargı, danıştay, idari dava'
    }
]

# Kanunları ekle
for law_data in laws_data:
    law_data.update({
        'legislation_type': kanun_turu,
        'status': 'active',
        'mevzuat_gov_id': law_data['number'],
        'source_url': f'https://www.mevzuat.gov.tr/mevzuat?MevzuatNo={law_data["number"]}',
        'pdf_url': f'https://www.mevzuat.gov.tr/MevzuatMetin/1.5.{law_data["number"]}.pdf'
    })
    
    law, created = ProfessionalLegislation.objects.get_or_create(
        number=law_data['number'],
        defaults=law_data
    )
    
    if created:
        print(f"✅ {law.title} ({law.number}) eklendi")
        
        # Her kanuna 1-2 örnek madde ekle
        sample_articles = {
            '2709': [{'article_number': '1', 'title': 'Devletin şekli', 'text': 'Türkiye Devleti bir Cumhuriyettir.'}],
            '4857': [{'article_number': '1', 'title': 'Amaç ve kapsam', 'text': 'Bu Kanunun amacı, işçi ve işveren ilişkilerini düzenlemektir.'}],
            '213': [{'article_number': '1', 'title': 'Vergi kanunu', 'text': 'Bu kanun, vergi ödevini yerine getirme şekil ve usullerini gösterir.'}],
            '6100': [{'article_number': '1', 'title': 'Amaç', 'text': 'Bu Kanunun amacı, hukuk yargısında uygulanacak usul ve esasları düzenlemektir.'}],
        }
        
        if law.number in sample_articles:
            for article_data in sample_articles[law.number]:
                article_data.update({
                    'legislation': law,
                    'order': 1
                })
                LegislationArticle.objects.create(**article_data)
                print(f"  → Madde {article_data['article_number']} eklendi")
    else:
        print(f"⚠️ {law.title} zaten mevcut")

print(f"\n🎉 TÜM 20 TEMEL KANUN TAMAMLANDI!")
print(f"📊 Toplam kanun sayısı: {ProfessionalLegislation.objects.count()}")
print(f"📊 Toplam madde sayısı: {LegislationArticle.objects.count()}")
print("\n📋 KANUN LİSTESİ:")
for law in ProfessionalLegislation.objects.all().order_by('number'):
    print(f"• {law.number} - {law.title} ({law.articles.count()} madde)")