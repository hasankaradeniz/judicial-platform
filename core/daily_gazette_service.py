from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from datetime import datetime, date, timedelta
import logging
from .models import DailyGazetteContent, EmailSubscription, DailyEmailSent
from .resmi_gazete_scraper import ResmiGazeteScraper
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)

class DailyGazetteEmailService:
    """
    Gunluk Resmi Gazete email gonderim servisi
    """
    
    def __init__(self):
        self.scraper = ResmiGazeteScraper()
    
    def scrape_and_save_daily_content(self, target_date=None):
        """
        Gunun Resmi Gazete icerigini cek ve veritabanina kaydet
        """
        if target_date is None:
            target_date = date.today()
        
        try:
            logger.info(f"Resmi Gazete icerigi cekiliyor: {target_date}")
            
            # Mevcut scraper i kullan
            scraped_content = self.scraper.get_daily_content(target_date)
            
            if not scraped_content:
                logger.warning(f"Hic icerik bulunamadi: {target_date}")
                return []
            
            saved_content = []
            
            for item in scraped_content:
                try:
                    # Var mi kontrol et
                    existing = DailyGazetteContent.objects.filter(
                        title=item["baslik"],
                        gazette_date=target_date
                    ).first()
                    
                    if existing:
                        logger.info(f"Zaten var: {item["baslik"][:50]}")
                        saved_content.append(existing)
                        continue
                    
                    # Kategori belirleme
                    content_type, category = self._determine_content_type_and_category(item)
                    
                    # Yeni icerik olustur
                    gazette_content = DailyGazetteContent.objects.create(
                        title=item["baslik"],
                        content_type=content_type,
                        category=category,
                        gazette_date=target_date,
                        gazette_number=item.get("sayi", ""),
                        original_url=item["link"],
                        summary=item.get("ozet", item["baslik"][:200]),
                        importance_score=self._calculate_importance_score(item),
                        scraping_source="resmigazete.gov.tr"
                    )
                    
                    saved_content.append(gazette_content)
                    logger.info(f"Yeni icerik kaydedildi: {gazette_content.title[:50]}")
                    
                except Exception as e:
                    logger.error(f"Icerik kaydetme hatasi: {str(e)} - {item.get(baslik, "Bilinmeyen")}")
                    continue
            
            logger.info(f"Toplam {len(saved_content)} icerik kaydedildi/guncellendi")
            return saved_content
            
        except Exception as e:
            logger.error(f"Scraping ve kaydetme hatasi: {str(e)}")
            return []
    
    def _determine_content_type_and_category(self, item):
        """
        AI destekli içerik kategorilendirme
        """
        try:
            # AI kategorilendirici import et
            from .ai_categorizer import ai_categorizer
            
            title = item.get("baslik", "")
            scraped_category = item.get("kategori", "")
            
            # AI ile kategorilendirme dene
            content_type, category = ai_categorizer.categorize_content(title, scraped_category)
            
            logger.info(f"AI Kategorilendirme - Başlık: {title[:50]} -> {category}")
            
            return content_type, category
            
        except Exception as e:
            logger.error(f"AI kategorilendirme hatası, fallback kullanılıyor: {e}")
            return self._fallback_categorize(item)
    
    def _fallback_categorize(self, item):
        """
        Fallback kategorilendirme
        """
        baslik = item.get("baslik", "").lower()
        kategori = item.get("kategori", "").lower()
        
        # Günlük sayı kontrolü
        if "resmi gazete" in baslik and "sayı" in baslik:
            return "yurutme_idare", "gunluk_sayi"
        
        # Yönetmelik kontrolü
        if "yönetmelik" in baslik:
            return "yurutme_idare", "yonetmelik"
        
        # Tebliğ kontrolü
        if "tebliğ" in baslik or "teblig" in baslik:
            return "yurutme_idare", "teblig"
        
        # Cumhurbaşkanlığı vekalet
        if "vekalet" in baslik or "vekâlet" in baslik:
            return "yurutme_idare", "cumhurbaskani_karari"
        
        # İçerik bazlı kategorilendirme
        if any(word in baslik for word in ["enerji", "elektrik", "transformatör"]):
            return "yurutme_idare", "cumhurbaskani_karari"
        
        if "vergi" in baslik:
            return "yurutme_idare", "cumhurbaskani_karari"
        
        if "sahipsiz hayvan" in baslik:
            return "yurutme_idare", "cumhurbaskani_karari"
        
        if "atama" in baslik:
            return "yurutme_idare", "atama_karari"
        
        # Varsayılan
        return "yurutme_idare", "other"
    def _calculate_importance_score(self, item):
        """
        Icerigin onem skorunu hesapla (1-10)
        """
        baslik = item.get("baslik", "").lower()
        
        # Yuksek oncelikli anahtar kelimeler
        high_priority = ["cumhurbaskanligi", "bakanlar kurulu", "anayasa mahkemesi", "yargitay"]
        medium_priority = ["yonetmelik", "atama karari", "kurul karari"]
        low_priority = ["teblig", "genelge", "ilan"]
        
        if any(word in baslik for word in high_priority):
            return 9
        elif any(word in baslik for word in medium_priority):
            return 7
        elif any(word in baslik for word in low_priority):
            return 5
        else:
            return 6
    
    def send_daily_emails(self, target_date=None):
        """
        Aktif abonelere gunluk email gonder
        """
        if target_date is None:
            target_date = date.today()
        
        try:
            logger.info(f"Gunluk email gonderimi basliyor: {target_date}")
            
            # Icerikleri cek ve kaydet
            daily_content = self.scrape_and_save_daily_content(target_date)
            
            if not daily_content:
                logger.warning("Gonderilecek icerik yok")
                return
            
            # Aktif aboneleri al
            subscriptions = EmailSubscription.objects.filter(
                is_active=True,
                frequency="daily"
            ).select_related("user")
            
            logger.info(f"Toplam {subscriptions.count()} aktif abone bulundu")
            
            success_count = 0
            error_count = 0
            
            for subscription in subscriptions:
                try:
                    if self._send_email_to_user(subscription, daily_content, target_date):
                        success_count += 1
                    else:
                        error_count += 1
                        
                except Exception as e:
                    logger.error(f"Email gonderme hatasi - {subscription.user.username}: {str(e)}")
                    error_count += 1
            
            logger.info(f"Email gonderimi tamamlandi - Basarili: {success_count}, Hata: {error_count}")
            
        except Exception as e:
            logger.error(f"Gunluk email gonderim hatasi: {str(e)}")
    
    def _send_email_to_user(self, subscription, content_list, target_date):
        """
        Belirli bir kullaniciya email gonder
        """
        try:
            user = subscription.user
            
            # Bu tarihte daha once email gonderilmis mi?
            existing_email = DailyEmailSent.objects.filter(
                user=user,
                email_date=target_date
            ).first()
            
            if existing_email:
                logger.info(f"Bu tarihte zaten email gonderilmis: {user.username} - {target_date}")
                return True
            
            # Email subject
            subject = f"LexatechAI - Gunluk Resmi Gazete Bulteni ({target_date.strftime('%d.%m.%Y')})"
            
            # HTML email icerigi olustur
            html_content = self._generate_email_html(user, content_list, target_date)
            
            # Email gonder
            send_mail(
                subject=subject,
                message=f"Gunluk Resmi Gazete ozeti - {len(content_list)} icerik",  # Plain text fallback
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_content,
                fail_silently=False,
            )
            
            # Email kaydini olustur
            email_sent = DailyEmailSent.objects.create(
                user=user,
                email_date=target_date,
                gazette_date=target_date,
                subject=subject,
                content_count=len(content_list),
                status="sent"
            )
            
            # Subscription güncelle
            subscription.last_email_sent = datetime.now()
            subscription.save()
            
            logger.info(f"Email gonderildi: {user.username} ({user.email})")
            return True
            
        except Exception as e:
            # Hata kaydini olustur
            DailyEmailSent.objects.create(
                user=subscription.user,
                email_date=target_date,
                gazette_date=target_date,
                subject=f"LexatechAI - Gunluk Resmi Gazete Bulteni ({target_date.strftime('%d.%m.%Y')})",
                content_count=len(content_list),
                status="failed",
                error_message=str(e)
            )
            
            logger.error(f"Email gonderim hatasi: {subscription.user.username} - {str(e)}")
            return False
    
    def _generate_email_html(self, user, content_list, target_date):
        """
        Email HTML icerigi olustur
        """
        context = {
            "user": user,
            "content_list": content_list,
            "target_date": target_date,
            "total_count": len(content_list),
            "categories": self._group_content_by_category(content_list),
            "unsubscribe_url": f"{settings.SITE_URL}/gazette/unsubscribe/{user.id}/",
        }
        
        # Simdilik basit HTML template kullan
        html_content = f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <title>LexatechAI - Gunluk Resmi Gazete Bulteni</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .header {{ background: #2c3e50; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .item {{ margin-bottom: 20px; padding: 15px; border-left: 4px solid #3498db; background: #f8f9fa; }}
                .category {{ font-weight: bold; color: #2c3e50; }}
                .title {{ font-size: 16px; font-weight: bold; margin: 5px 0; }}
                .summary {{ color: #666; }}
                .link {{ color: #3498db; text-decoration: none; }}
                .footer {{ text-align: center; padding: 20px; background: #ecf0f1; }}
            </style>
        </head>
        <body>
            <div class="header">
                <div class="logo"><img src="https://via.placeholder.com/180x60/667eea/ffffff?text=LexatechAI" alt="LexatechAI" style="max-width: 200px; height: auto;" /></div><h1>LexatechAI</h1>
                <h2>Gunluk Resmi Gazete Bulteni</h2>
                <p>{target_date.strftime("%d.%m.%Y")} - {len(content_list)} İçerik</p>
            </div>
            
            <div class="content">
                <p>Merhaba {user.first_name + " " + user.last_name if user.first_name and user.last_name else user.first_name or user.username},</p>
                <p>Bugunun Resmi Gazete iceriklerini sizin icin derledik:</p>
        """
        
        sorted_content = self._sort_content_by_gazette_order(content_list)
        for item in sorted_content[:15]:  # İlk 15 icerigi goster
            html_content += f"""
                <div class="item">
                    <div class="category">{item.get_enhanced_category_display()}</div>
                    <div class="title">{item.title}</div>
                    <div class="summary">{item.get_enhanced_summary()}</div>
                    <div><a href="{item.original_url}" class="link">Detayları Görüntüle →</a></div>
                </div>
            """
        
        html_content += f"""
            </div>
            
            <div class="footer">
                <p>Bu email LexatechAI AI tarafindan otomatik olarak gonderilmistir.</p>
                <p><a href="https://lexatech.ai">LexatechAI.ai</a> | <a href="" + context.get("unsubscribe_url", "#") + "">Abonelikten Cik</a></p>
            </div>
        </body>
        </html>
        """
        
        return html_content
    
    def _group_content_by_category(self, content_list):
        """
        Icerikleri kategoriye gore grupla
        """
        categories = {}
        for item in content_list:
            cat = item.get_enhanced_category_display()
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(item)
        return categories
    
    def test_email_system(self, user_email):
        """
        Email sistemini test et
        """
        try:
            logger.info(f"Email sistemi test ediliyor: {user_email}")
            
            # Test kullanıcısı için gerçek DailyGazetteContent objesi oluştur
            from .models import DailyGazetteContent
            from datetime import date
            
            # Test content objesi oluştur
            class TestContent:
                def __init__(self):
                    self.title = "📰 Günlük Sayı - Test"
                    self.category = "gunluk_sayi"
                    self.original_url = "https://resmigazete.gov.tr"
                    self.id = 1
                    self.gazette_date = date.today()
                
                def get_enhanced_category_display(self):
                    return "📰 Günlük Sayı"
                
                def get_enhanced_summary(self):
                    return "Bugün yayınlanmış olan Resmi Gazete'nin bir bütün olarak PDF metni"
            
            class TestContent2:
                def __init__(self):
                    self.title = "⚖️ Test Cumhurbaşkanı Kararı"
                    self.category = "cumhurbaskani_karari"
                    self.original_url = "https://resmigazete.gov.tr/test-karar"
                    self.id = 2
                    self.gazette_date = date.today()
                
                def get_enhanced_category_display(self):
                    return "⚖️ Cumhurbaşkanı Kararı"
                
                def get_enhanced_summary(self):
                    return "Test amaçlı Cumhurbaşkanı kararı örneği. Bu karar, yeni düzenlemeler ve uygulamalar hakkında detaylı bilgi vermektedir."
            
            test_content = [TestContent(), TestContent2()]
            
            # Test kullanicisi
            class TestUser:
                def __init__(self, email):
                    self.email = email
                    self.username = "test_user"
                    self.first_name = "Hasan"
                    self.last_name = "Karadeniz"
                    self.id = 1
            
            user = TestUser(user_email)
            
            # HTML olustur
            html_content = self._generate_email_html(user, test_content, date.today())
            
            # Email gonder
            send_mail(
                subject="LexatechAI - Test Email",
                message="Bu bir test emailidir.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user_email],
                html_message=html_content,
                fail_silently=False,
            )
            
            logger.info(f"Test email basariyla gonderildi: {user_email}")
            return True
            
        except Exception as e:
            logger.error(f"Test email hatasi: {str(e)}")
            return False

    def _sort_content_by_gazette_order(self, content_list):
        """Resmi Gazete siralamasina gore icerik sirala"""
        order_priority = {
            'gunluk_sayi': 1,
            'cumhurbaskani_karari': 2,
            'cumhurbaskanligi_vekalet': 3,
            'yonetmelik': 4,
            'teblig': 5,
            'ilan': 6,
            'other': 99
        }
        
        def get_sort_key(item):
            category = item.category
            priority = order_priority.get(category, 50)
            return (priority, item.id)
        
        return sorted(content_list, key=get_sort_key)
