import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "judicial_platform.settings")
django.setup()

from core.models import DailyGazetteContent
from core.ai_categorizer import ai_categorizer
from datetime import date

print("🤖 AI İLE YENİDEN KATEGORİLENDİRME")
print("="*50)

# Bugünkü içerikleri güncelle
today_content = DailyGazetteContent.objects.filter(gazette_date=date.today())

print(f"📊 Güncellenecek içerik sayısı: {today_content.count()}")

for item in today_content:
    old_category = item.category
    
    # AI ile yeniden kategorilendır
    try:
        content_type, new_category = ai_categorizer.categorize_content(item.title, "")
        
        if old_category != new_category:
            item.category = new_category
            item.content_type = content_type
            item.save()
            
            print(f"✅ Güncellendi: {item.title[:50]}")
            print(f"   {old_category} -> {new_category}")
            print()
        else:
            print(f"⚪ Değişiklik yok: {item.title[:50]} ({new_category})")
            
    except Exception as e:
        print(f"❌ Hata: {item.title[:50]} - {e}")

print("\n🎯 YENİ KATEGORİ DAĞILIMI:")
categories = {}
for item in DailyGazetteContent.objects.filter(gazette_date=date.today()):
    if item.category not in categories:
        categories[item.category] = 0
    categories[item.category] += 1

for category, count in categories.items():
    print(f"   {category}: {count} içerik")

print("\nAI kategorilendirme tamamlandı\!")
