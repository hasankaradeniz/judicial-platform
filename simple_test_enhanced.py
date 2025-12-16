import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "judicial_platform.settings")
django.setup()

from core.models import DailyGazetteContent
from datetime import date

# İlk içeriği test et
item = DailyGazetteContent.objects.filter(gazette_date=date.today()).first()

if item:
    print(f"İçerik: {item.title}")
    print(f"Kategori: {item.category}")
    print(f"get_category_display(): {item.get_category_display()}")
    
    try:
        print(f"get_enhanced_category_display(): {item.get_enhanced_category_display()}")
    except AttributeError as e:
        print(f"Enhanced metod hatası: {e}")
        
    try:
        print(f"get_enhanced_summary(): {item.get_enhanced_summary()}")
    except AttributeError as e:
        print(f"Enhanced summary hatası: {e}")
        
else:
    print("İçerik bulunamadı")
