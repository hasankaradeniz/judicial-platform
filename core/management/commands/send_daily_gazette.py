from django.core.management.base import BaseCommand
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.contrib.auth.models import User
from datetime import datetime, timedelta
import logging
import time
from core.resmi_gazete_service import ResmiGazeteService
from core.management.commands.scrape_resmi_gazete import Command as ScrapeCommand
from core.models import UserProfile

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Günlük Resmi Gazete özetini üyelere mail olarak gönderir'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='Belirli bir tarih için gönder (YYYY-MM-DD formatında)'
        )
        parser.add_argument(
            '--test-email',
            type=str,
            help='Test için belirli bir email adresine gönder'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Gerçek email göndermeden test et'
        )

    def handle(self, *args, **options):
        target_date = options['date']
        test_email = options['test_email']
        dry_run = options['dry_run']
        
        if target_date:
            try:
                target_date = datetime.strptime(target_date, '%Y-%m-%d').date()
            except ValueError:
                self.stdout.write(
                    self.style.ERROR('Hatalı tarih formatı. YYYY-MM-DD kullanın.')
                )
                return
        else:
            target_date = datetime.now().date()

        self.stdout.write(f'Günlük Resmi Gazete emaili hazırlanıyor - Tarih: {target_date}')
        
        try:
            # 1. Resmi Gazete içeriğini scrape et (mevcut sistem kullanılıyor)
            self.stdout.write('1. Resmi Gazete scraping...')
            from core.resmi_gazete_scraper import ResmiGazeteScraper
            scraper = ResmiGazeteScraper()
            raw_content = scraper.get_daily_content(target_date)
            
            # İçeriği uygun formata çevir
            gazette_content = self.convert_to_gazette_format(raw_content, target_date)
            
            if not gazette_content:
                self.stdout.write(
                    self.style.ERROR('Resmi Gazete içeriği alınamadı')
                )
                return
            
            # 2. AI ile özet oluştur
            self.stdout.write('2. AI özet oluşturuluyor...')
            rg_service = ResmiGazeteService()
            summary = rg_service.create_daily_summary(gazette_content)
            
            if not summary:
                self.stdout.write(
                    self.style.ERROR('AI özet oluşturulamadı')
                )
                return
            
            # 3. Email içeriği hazırla
            self.stdout.write('3. Email içeriği hazırlanıyor...')
            email_content = rg_service.generate_email_content(summary)
            
            if not email_content:
                self.stdout.write(
                    self.style.ERROR('Email içeriği oluşturulamadı')
                )
                return
            
            # DEBUG: İçerik kontrolü
            self.stdout.write(f'   Özet bölüm sayısı: {len(summary.get("sections", []))}')
            if summary.get('sections'):
                for i, section in enumerate(summary.get('sections', [])[:2]):
                    self.stdout.write(f'     Bölüm {i+1}: {section.get("title", "NO_TITLE")} - {len(section.get("subsections", []))} alt bölüm')
            else:
                self.stdout.write('     ⚠️  Özet bölümleri boş!')
            
            # 4. Email gönder
            self.stdout.write('4. Emailler gönderiliyor...')
            sent_count = self.send_emails(email_content, test_email, dry_run)
            
            self.stdout.write(
                self.style.SUCCESS(f'İşlem tamamlandı. {sent_count} email gönderildi.')
            )
            
        except Exception as e:
            logger.error(f"Günlük gazete gönderimi hatası: {e}")
            self.stdout.write(
                self.style.ERROR(f'Hata: {e}')
            )

    def convert_to_gazette_format(self, raw_content, target_date):
        """Mevcut scraper çıktısını AI sistemi için uygun formata çevirir"""
        try:
            if not raw_content:
                return None
            
            # Bölümleri kategorilere göre grupla
            sections = {
                'YÜRÜTME VE İDARE BÖLÜMÜ': [],
                'YARGI BÖLÜMÜ': [],
                'İLÂN BÖLÜMÜ': []
            }
            
            # Full text oluştur
            full_text_parts = []
            
            for item in raw_content:
                title = item.get('baslik', '')
                category = item.get('kategori', '')
                summary = item.get('ozet', '')
                content_type = item.get('tur', '')
                
                # Kategori belirle - daha akıllı sınıflandırma
                section_key = 'İLÂN BÖLÜMÜ'  # Default
                
                # Başlık ve kategori bazlı sınıflandırma
                title_lower = title.lower()
                category_lower = category.lower()
                combined_text = f"{title_lower} {category_lower} {summary.lower() if summary else ''}"
                
                # YÜRÜTME VE İDARE BÖLÜMÜ - idari düzenlemeler
                if any(term in combined_text for term in [
                    'yönetmelik', 'tebliğ', 'kurul kararı', 'bakanlar kurulu',
                    'cumhurbaşkanı kararı', 'genelge', 'tamim', 'yönerge',
                    'bakanl', 'müdürlük', 'genel müdürlük'
                ]):
                    section_key = 'YÜRÜTME VE İDARE BÖLÜMÜ'
                elif any(term in combined_text for term in ['sayıştay', 'mahkeme', 'yargı', 'karar']):
                    section_key = 'YARGI BÖLÜMÜ'
                
                # Content'i temizle - "İdari İşlem" prefix'i ekleme
                clean_content = summary or title
                if not clean_content or clean_content.strip() == title:
                    clean_content = f"Bu düzenleme {title.lower()} ile ilgili yeni bir düzenlemedir."
                
                sections[section_key].append({
                    'title': title,
                    'content': clean_content,
                    'category': category,
                    'link': item.get('link', 'https://www.resmigazete.gov.tr/')
                })
                
                # Full text'e ekle
                full_text_parts.append(f"{title}\n{summary}\n")
            
            return {
                'date': target_date.strftime('%d.%m.%Y'),
                'sections': sections,
                'full_text': '\n'.join(full_text_parts),
                'item_count': len(raw_content)
            }
            
        except Exception as e:
            logger.error(f"Format çevirme hatası: {e}")
            return None

    def send_emails(self, email_content, test_email=None, dry_run=False):
        """Email gönderim işlemi"""
        
        sent_count = 0
        
        try:
            # Alıcı listesini belirle
            if test_email:
                recipients = [test_email]
                self.stdout.write(f'Test modu: {test_email}')
            else:
                # Aktif üyeleri al (ücretsiz deneme veya ücretli abonelik)
                recipients = self.get_active_subscribers()
                self.stdout.write(f'Toplam alıcı: {len(recipients)}')
            
            if dry_run:
                self.stdout.write(
                    self.style.WARNING(f'DRY RUN: {len(recipients)} kişiye email gönderilecekti')
                )
                self.stdout.write(f"Email başlığı: {email_content['subject']}")
                self.stdout.write(f"İçerik uzunluğu: {len(email_content['html_content'])} karakter")
                return len(recipients)
            
            # Toplu email gönder
            batch_size = 50  # Gmail limitleri için batch olarak gönder
            
            for i in range(0, len(recipients), batch_size):
                batch = recipients[i:i + batch_size]
                
                try:
                    # Email oluştur
                    msg = EmailMultiAlternatives(
                        subject=email_content['subject'],
                        body=email_content['plain_text'],
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        bcc=batch  # BCC ile gizli gönderim
                    )
                    
                    # HTML içerik ekle
                    msg.attach_alternative(email_content['html_content'], "text/html")
                    
                    # Gönder
                    msg.send()
                    sent_count += len(batch)
                    
                    self.stdout.write(f'Batch gönderildi: {i + 1}-{min(i + batch_size, len(recipients))}')
                    
                    # Rate limiting için bekle
                    if i + batch_size < len(recipients):
                        time.sleep(2)
                    
                except Exception as e:
                    logger.error(f"Email batch gönderimi hatası: {e}")
                    self.stdout.write(
                        self.style.ERROR(f'Batch {i//batch_size + 1} hatası: {e}')
                    )
                    continue
            
            return sent_count
            
        except Exception as e:
            logger.error(f"Email gönderim hatası: {e}")
            raise

    def get_active_subscribers(self):
        """Aktif abonelerin email listesini döndürür"""
        
        try:
            active_emails = []
            
            # TEST MODU: Sadece hasankaradeniz kullanıcısına gönder
            users = User.objects.filter(
                is_active=True, 
                username='hasankaradeniz'
            )
            
            for user in users:
                if not user.email:
                    continue
                
                # Tüm kayıtlı kullanıcılara resmi gazete gönder
                active_emails.append(user.email)
            
            # Duplicate email'leri temizle
            active_emails = list(set(active_emails))
            
            self.stdout.write(f'Aktif kullanıcı sayısı: {len(active_emails)}')
            
            return active_emails
            
        except Exception as e:
            logger.error(f"Aktif kullanıcı listesi hatası: {e}")
            return []