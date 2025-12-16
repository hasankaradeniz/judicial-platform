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
    print("🎯 FINAL TEST - Logo ve Metin Düzeltmeleri")
    print("="*50)
    
    # Bugünkü içerikleri al
    content_list = DailyGazetteContent.objects.filter(gazette_date=date.today())
    print(f"📊 Toplam {content_list.count()} içerik")
    
    # Kategorileri göster
    print("\n📋 KATEGORİ DAĞILIMI:")
    categories = {}
    for item in content_list:
        cat = item.get_enhanced_category_display()
        if cat not in categories:
            categories[cat] = 0
        categories[cat] += 1
    
    for category, count in categories.items():
        print(f"   {category}: {count} içerik")
    
    # İdari işlem kategorisindeki özetleri kontrol et
    print("\n🔍 İDARİ İŞLEM ÖZETLERİ:")
    other_items = content_list.filter(category="other")
    for item in other_items[:2]:
        print(f"   📄 {item.title[:50]}...")
        print(f"   💬 {item.get_enhanced_summary()[:80]}...")
        print()
    
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
        print("📧 Email HTML içeriği oluşturuldu")
        
        # Email gönder
        today_str = date.today().strftime("%d.%m.%Y")
        send_mail(
            subject=f"LexatechAI - FIXED Resmi Gazete Bülteni ({today_str})",
            message="Logo ve metin düzeltmeleri ile günlük resmi gazete bülteni.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=["hasankaradeniz@gmail.com"],
            html_message=html_content,
            fail_silently=False,
        )
        
        print(f"\n🎉 FIXED email başarıyla gönderildi\!")
        print("\n✅ DÜZELTMELER:")
        print("🖼️ Logo: Placeholder URL ile görünür logo")
        print("📝 Metin: Other -> İdari İşlem kapsamında")
        print("⚖️ Kategoriler: AI destekli doğru sınıflandırma")
        print("👤 Kişisel: Hasan Karadeniz")
        print("🏢 Branding: LexatechAI")
        
    else:
        print("❌ İçerik bulunamadı")

except Exception as e:
    print(f"❌ Hata: {e}")
    import traceback
    traceback.print_exc()
