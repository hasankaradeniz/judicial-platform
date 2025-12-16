import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "judicial_platform.settings")
django.setup()

from core.models import DailyGazetteContent
from datetime import date

# Bugünkü içerikleri güncelle
today_content = DailyGazetteContent.objects.filter(gazette_date=date.today())

print(f"Güncellenecek içerik sayısı: {today_content.count()}")

for item in today_content:
    old_category = item.category
    
    title_lower = item.title.lower()
    
    # Kategorileri yeniden belirle
    if "resmi gazete" in title_lower and "sayı" in title_lower:
        item.category = "gunluk_sayi"
    elif any(word in title_lower for word in ["cumhurbaşkanı", "cumhurbaskani", "vekalet"]):
        item.category = "cumhurbaskani_karari"
    elif any(word in title_lower for word in ["atama kararı", "atama"]):
        item.category = "atama_karari" 
    elif any(word in title_lower for word in ["yönetmelik"]):
        item.category = "yonetmelik"
    elif any(word in title_lower for word in ["tebliğ"]):
        item.category = "teblig"
    elif any(word in title_lower for word in ["genelge"]):
        item.category = "genelge"
    
    if old_category != item.category:
        item.save()
        print(f"Güncellendi: {item.title[:50]} - {old_category} -> {item.category}")

print("Kategori güncellemesi tamamlandı\!")
