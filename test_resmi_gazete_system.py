#!/usr/bin/env python
"""
Resmi Gazete email sistemi test script'i
"""

import os
import sys
import django

# Django setup
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'judicial_platform.settings')
django.setup()

from datetime import datetime, timedelta
from core.management.commands.scrape_resmi_gazete import Command as ScrapeCommand
from core.resmi_gazete_service import ResmiGazeteService
from core.management.commands.send_daily_gazette import Command as EmailCommand

def test_full_system():
    """Tam sistem testi"""
    print("=" * 60)
    print("RESMI GAZETE EMAIL SİSTEMİ TEST")
    print("=" * 60)
    
    # Test tarihi - bugün
    test_date = datetime.now().date()
    print(f"Test Tarihi: {test_date}")
    print()
    
    try:
        # 1. Scraping testi
        print("1. SCRAPING TESTİ")
        print("-" * 30)
        scraper = ScrapeCommand()
        print(f"Resmi Gazete scraping başladı - {test_date}")
        
        content = scraper.scrape_resmi_gazete(test_date)
        if content:
            print(f"✅ Scraping başarılı - İçerik uzunluğu: {len(content.get('full_text', ''))} karakter")
            print(f"   Bulunan bölüm sayısı: {len(content.get('sections', []))}")
        else:
            print("❌ Scraping başarısız")
            return False
        
        print()
        
        # 2. AI Özet testi  
        print("2. AI ÖZET TESTİ")
        print("-" * 30)
        rg_service = ResmiGazeteService()
        
        if not rg_service.model:
            print("❌ Gemini API yapılandırması bulunamadı")
            return False
        
        print("AI özet oluşturuluyor...")
        summary = rg_service.create_daily_summary(content)
        
        if summary:
            print(f"✅ AI özet başarılı")
            print(f"   Ana bölüm sayısı: {len(summary.get('sections', []))}")
            
            # Özet detayları
            for section in summary.get('sections', [])[:2]:  # İlk 2 bölümü göster
                print(f"   - {section['title']}: {len(section.get('subsections', []))} alt bölüm")
        else:
            print("❌ AI özet oluşturulamadı")
            return False
        
        print()
        
        # 3. Email içerik testi
        print("3. EMAIL İÇERİK TESTİ")
        print("-" * 30)
        print("Email içeriği hazırlanıyor...")
        
        email_content = rg_service.generate_email_content(summary)
        
        if email_content:
            print(f"✅ Email içerik başarılı")
            print(f"   Başlık: {email_content['subject']}")
            print(f"   HTML uzunluğu: {len(email_content['html_content'])} karakter")
            print(f"   Plain text uzunluğu: {len(email_content['plain_text'])} karakter")
        else:
            print("❌ Email içerik oluşturulamadı")
            return False
        
        print()
        
        # 4. Test email gönderimi
        print("4. TEST EMAIL GÖNDERİMİ")
        print("-" * 30)
        
        test_email = input("Test email adresi girin (enter=skip): ").strip()
        
        if test_email and '@' in test_email:
            print(f"Test email gönderiliyor: {test_email}")
            
            email_cmd = EmailCommand()
            
            # Dry run testi
            print("  Dry run testi...")
            sent_count = email_cmd.send_emails(email_content, test_email, dry_run=True)
            print(f"  ✅ Dry run başarılı - {sent_count} email gönderilecek")
            
            # Gerçek gönderim onayı
            real_send = input("  Gerçek email gönderilsin mi? (y/N): ").lower().strip()
            
            if real_send == 'y':
                print("  Gerçek email gönderiliyor...")
                sent_count = email_cmd.send_emails(email_content, test_email, dry_run=False)
                print(f"  ✅ Email gönderildi - {sent_count} email")
            else:
                print("  ⏭️  Gerçek email gönderimi atlandı")
        else:
            print("⏭️  Test email gönderimi atlandı")
        
        print()
        print("=" * 60)
        print("✅ TÜM TESTLER BAŞARILI!")
        print("✅ Sistem production'a hazır")
        print("=" * 60)
        
        # Kurulum bilgileri
        print()
        print("KURULUM BİLGİLERİ:")
        print("- Management command: python manage.py send_daily_gazette")
        print("- Test komutu: python manage.py send_daily_gazette --test-email=test@example.com")
        print("- Celery task: core.tasks.send_daily_gazette_emails")
        print("- Otomatik çalışma: Her gün sabah 09:00 (Celery Beat)")
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ Test hatası: {e}")
        import traceback
        traceback.print_exc()
        return False

def quick_test():
    """Hızlı API testi"""
    print("Hızlı API Test")
    print("-" * 30)
    
    try:
        rg_service = ResmiGazeteService()
        
        if rg_service.model:
            print("✅ Gemini API bağlantısı OK")
        else:
            print("❌ Gemini API yapılandırma hatası")
            
        # Mock content ile test
        mock_content = {
            'date': '13.12.2025',
            'sections': [],
            'full_text': 'Test resmi gazete içeriği. YÖNETMELİKLER bölümünde yeni düzenlemeler var.'
        }
        
        summary = rg_service.create_daily_summary(mock_content)
        
        if summary:
            print("✅ AI özet sistemi çalışıyor")
            return True
        else:
            print("❌ AI özet sistemi hatası")
            return False
            
    except Exception as e:
        print(f"❌ Hızlı test hatası: {e}")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Resmi Gazete sistemi test')
    parser.add_argument('--quick', action='store_true', help='Hızlı test')
    parser.add_argument('--full', action='store_true', help='Tam test')
    
    args = parser.parse_args()
    
    if args.quick:
        success = quick_test()
    elif args.full:
        success = test_full_system()
    else:
        print("Test modu seçin:")
        print("  python test_resmi_gazete_system.py --quick   # Hızlı test")
        print("  python test_resmi_gazete_system.py --full    # Tam test")
        sys.exit(1)
    
    sys.exit(0 if success else 1)