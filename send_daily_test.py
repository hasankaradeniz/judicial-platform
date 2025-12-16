from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from datetime import datetime, date
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "judicial_platform.settings")
django.setup()

from core.daily_gazette_service import DailyGazetteEmailService

service = DailyGazetteEmailService()
print("Bugunun resmi gazete icerigi gonderiliyor...")

# Bugunun icerigini cek ve email olarak gonder
try:
    # Once icerik varligini kontrol et
    content = service.scrape_and_save_daily_content(date.today())
    print(f"Toplam {len(content)} icerik bulundu")
    
    if content:
        # Test kullanicisi olustur
        class TestUser:
            def __init__(self, email):
                self.email = email
                self.username = "Test User"
                self.first_name = "Test"
                self.id = 999999
        
        user = TestUser("hasankaradeniz@gmail.com")
        
        # Email HTML icerigini olustur
        html_content = service._generate_email_html(user, content, date.today())
        
        # Email gonder
        today_str = date.today().strftime("%d.%m.%Y")
        send_mail(
            subject=f"LexaTech - Gunluk Resmi Gazete Bulteni ({today_str})",
            message="Gunluk resmi gazete iceriklerini HTML formatinda goruntuleyebilirsiniz.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=["hasankaradeniz@gmail.com"],
            html_message=html_content,
            fail_silently=False,
        )
        
        print("Gunluk resmi gazete email i basariyla gonderildi\!")
    else:
        print("Bugune ait icerik bulunamadi")

except Exception as e:
    print(f"Hata: {e}")
    import traceback
    traceback.print_exc()
