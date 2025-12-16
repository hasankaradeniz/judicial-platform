from django.core.mail import send_mail
from django.conf import settings
from datetime import date
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "judicial_platform.settings")
django.setup()

from core.daily_gazette_service import DailyGazetteEmailService
from core.models import DailyGazetteContent

try:
    print("🤖 AI Enhanced Email Sistemi - Final Test")
    print("="*60)
    
    # Bugünkü içerikleri al
    content_list = DailyGazetteContent.objects.filter(gazette_date=date.today())
    print(f"📊 Toplam {content_list.count()} içerik bulundu")
    
    # İçerik örnekleri göster
    print("\n🔍 AI Enhanced Özetler:")
    for i, item in enumerate(content_list[:3], 1):
        print(f"\n{i}. {item.get_enhanced_category_display()}")
        print(f"   📝 Başlık: {item.title[:70]}...")
        print(f"   🤖 AI Özet: {item.get_enhanced_summary()[:120]}...")
    
    if content_list:
        # Email servisini başlat
        service = DailyGazetteEmailService()
        
        # Test kullanıcısı oluştur
        class TestUser:
            def __init__(self):
                self.email = "hasankaradeniz@gmail.com"
                self.username = "hasankaradeniz"
                self.first_name = "Hasan"
                self.last_name = "Karadeniz"
                self.id = 999999
        
        user = TestUser()
        
        # Email HTML oluştur
        html_content = service._generate_email_html(user, list(content_list), date.today())
        print(f"\n📧 AI Enhanced email HTML içeriği oluşturuldu")
        
        # Email gönder
        today_str = date.today().strftime("%d.%m.%Y")
        send_mail(
            subject=f"LexatechAI - AI Enhanced Resmi Gazete Bülteni ({today_str})",
            message="AI destekli detaylı içerik analizi ile günlük resmi gazete bülteni.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=["hasankaradeniz@gmail.com"],
            html_message=html_content,
            fail_silently=False,
        )
        
        print(f"\n🎉 AI Enhanced email başarıyla gönderildi\!")
        print("\n✨ Yeni AI Özellikler:")
        print("🤖 AI destekli içerik analizi")
        print("📝 Otomatik detaylı özetler")
        print("🎯 İçeriğe özel açıklamalar")
        print("🔍 Akıllı kategorilendirme")
        print("👤 Kişisel selamlama: Hasan Karadeniz")
        print("🏢 LexatechAI branding")
        print("🖼️ Logo entegrasyonu")
        
    else:
        print("❌ İçerik bulunamadı")

except Exception as e:
    print(f"❌ Hata: {e}")
    import traceback
    traceback.print_exc()
