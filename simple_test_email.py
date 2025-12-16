from django.core.mail import send_mail
from django.conf import settings
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "judicial_platform.settings")
django.setup()

try:
    send_mail(
        subject="LexaTech - Test Email",
        message="Bu bir test emailidir. Gunluk resmi gazete sistemi test ediliyor.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=["hasankaradeniz@gmail.com"],
        fail_silently=False,
    )
    print("Test email basariyla gonderildi\!")
except Exception as e:
    print(f"Test email hatasi: {e}")
    print(f"Email ayarlari:")
    print(f"EMAIL_HOST: {getattr(settings, EMAIL_HOST, None)}")
    print(f"EMAIL_PORT: {getattr(settings, EMAIL_PORT, None)}")
    print(f"EMAIL_USE_TLS: {getattr(settings, EMAIL_USE_TLS, None)}")
    print(f"DEFAULT_FROM_EMAIL: {getattr(settings, DEFAULT_FROM_EMAIL, None)}")
