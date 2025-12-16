import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "judicial_platform.settings")
django.setup()

from core.models import DailyGazetteContent
from datetime import date

print("🔍 KATEGORİLENDİRME ANALİZİ")
print("="*50)

# Bugünkü içerikleri analiz et
content_list = DailyGazetteContent.objects.filter(gazette_date=date.today())

categories = {}
for item in content_list:
    if item.category not in categories:
        categories[item.category] = []
    categories[item.category].append(item)

print("📊 Mevcut Kategoriler:")
for category, items in categories.items():
    print(f"\n{category} ({len(items)} içerik):")
    for i, item in enumerate(items[:3], 1):
        print(f"  {i}. {item.title[:80]}...")

print("\n🤖 SCRAPING VERİSİ ANALİZİ:")
print("Resmi Gazete scraping sırasında kategoriler nasıl geliyor:")

from core.daily_gazette_service import DailyGazetteEmailService
service = DailyGazetteEmailService()

# Son scraping verilerini kontrol et
scraped_data = service.scraper.get_daily_content(date.today())
print(f"\nToplam {len(scraped_data)} scraping verisi:")

for i, item in enumerate(scraped_data[:5], 1):
    print(f"\n{i}. Scraping Verisi:")
    print(f"   Başlık: {item.get(baslik, N/A)[:60]}...")
    print(f"   Kategori: {item.get(kategori, N/A)}")
    print(f"   Tür: {item.get(tur, N/A)}")
    
    # Bu veri nasıl kategorilendiriliyor?
    content_type, category = service._determine_content_type_and_category(item)
    print(f"   -> Belirlenen kategori: {category}")
