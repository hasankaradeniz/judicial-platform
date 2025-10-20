# Temel mevzuat türleri ve kategorilerini yükleyen script
# Django shell ile çalıştırılacak

from core.models import LegislationType, LegislationCategory

# Mevzuat türlerini yükle
legislation_types = [
    {
        'name': 'Kanun',
        'code': 'kanun',
        'hierarchy_level': 2,
        'display_order': 1,
        'color_code': '#dc3545',
        'icon_class': 'fas fa-balance-scale'
    },
    {
        'name': 'Cumhurbaşkanlığı Kararnamesi',
        'code': 'cbk',
        'hierarchy_level': 3,
        'display_order': 2,
        'color_code': '#6f42c1',
        'icon_class': 'fas fa-crown'
    },
    {
        'name': 'Yönetmelik',
        'code': 'yonetmelik',
        'hierarchy_level': 4,
        'display_order': 3,
        'color_code': '#007bff',
        'icon_class': 'fas fa-cogs'
    },
    {
        'name': 'Tebliğ',
        'code': 'teblig',
        'hierarchy_level': 5,
        'display_order': 4,
        'color_code': '#28a745',
        'icon_class': 'fas fa-bullhorn'
    },
    {
        'name': 'Genelge',
        'code': 'genelge',
        'hierarchy_level': 6,
        'display_order': 5,
        'color_code': '#ffc107',
        'icon_class': 'fas fa-envelope'
    },
    {
        'name': 'Tüzük',
        'code': 'tuzuk',
        'hierarchy_level': 4,
        'display_order': 6,
        'color_code': '#fd7e14',
        'icon_class': 'fas fa-book'
    }
]

for lt_data in legislation_types:
    lt, created = LegislationType.objects.get_or_create(
        code=lt_data['code'],
        defaults=lt_data
    )
    if created:
        print(f"✓ {lt.name} türü oluşturuldu")
    else:
        print(f"- {lt.name} türü zaten mevcut")

# Mevzuat kategorilerini yükle
categories = [
    {
        'name': 'Medeni Hukuk',
        'code': 'medeni',
        'slug': 'medeni-hukuk',
        'description': 'Kişi hakları, aile hukuku, miras hukuku, eşya hukuku',
        'icon_class': 'fas fa-users',
        'color_code': '#17a2b8',
        'display_order': 1
    },
    {
        'name': 'Borçlar Hukuku',
        'code': 'borclar',
        'slug': 'borclar-hukuku',
        'description': 'Sözleşmeler, haksız fiiller, sebepsiz zenginleşme',
        'icon_class': 'fas fa-handshake',
        'color_code': '#6f42c1',
        'display_order': 2
    },
    {
        'name': 'Ticaret Hukuku',
        'code': 'ticaret',
        'slug': 'ticaret-hukuku',
        'description': 'Ticari işletme, şirketler, ticari senetler, sigorta',
        'icon_class': 'fas fa-briefcase',
        'color_code': '#28a745',
        'display_order': 3
    },
    {
        'name': 'Ceza Hukuku',
        'code': 'ceza',
        'slug': 'ceza-hukuku',
        'description': 'Suçlar, cezalar, ceza muhakemesi',
        'icon_class': 'fas fa-gavel',
        'color_code': '#dc3545',
        'display_order': 4
    },
    {
        'name': 'İdare Hukuku',
        'code': 'idare',
        'slug': 'idare-hukuku',
        'description': 'Kamu yönetimi, idari işlemler, idari yargı',
        'icon_class': 'fas fa-university',
        'color_code': '#ffc107',
        'display_order': 5
    },
    {
        'name': 'Vergi Hukuku',
        'code': 'vergi',
        'slug': 'vergi-hukuku',
        'description': 'Gelir vergisi, KDV, diğer vergiler',
        'icon_class': 'fas fa-calculator',
        'color_code': '#fd7e14',
        'display_order': 6
    },
    {
        'name': 'İş ve Sosyal Güvenlik Hukuku',
        'code': 'is_sosyal',
        'slug': 'is-sosyal-guvenlik',
        'description': 'İş sözleşmeleri, işçi hakları, sosyal sigorta',
        'icon_class': 'fas fa-hard-hat',
        'color_code': '#20c997',
        'display_order': 7
    },
    {
        'name': 'Anayasa Hukuku',
        'code': 'anayasa',
        'slug': 'anayasa-hukuku',
        'description': 'Temel haklar, devlet örgütü, anayasa yargısı',
        'icon_class': 'fas fa-flag',
        'color_code': '#e83e8c',
        'display_order': 8
    }
]

for cat_data in categories:
    cat, created = LegislationCategory.objects.get_or_create(
        code=cat_data['code'],
        defaults=cat_data
    )
    if created:
        print(f"✓ {cat.name} kategorisi oluşturuldu")
    else:
        print(f"- {cat.name} kategorisi zaten mevcut")

print("\\n🎉 Temel veriler başarıyla yüklendi!")
print(f"📊 {LegislationType.objects.count()} mevzuat türü")
print(f"📁 {LegislationCategory.objects.count()} kategori")