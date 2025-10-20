# Django Management Command - Mevzuat Scraping
# /var/www/judicial_platform/core/management/commands/scrape_mevzuat.py

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from core.scraper import MevzuatScraper, save_to_database
import logging
from datetime import datetime

class Command(BaseCommand):
    help = 'Mevzuat.gov.tr\'den tüm mevzuatları çeker ve veritabanına kaydeder'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=100,
            help='Kaç adet mevzuat işlenecek (varsayılan: 100)'
        )
        parser.add_argument(
            '--test-mode',
            action='store_true',
            help='Test modu - sadece 5 mevzuat işlenir'
        )
        parser.add_argument(
            '--update-only',
            action='store_true',
            help='Sadece mevcut mevzuatları güncelle'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Detaylı çıktı göster'
        )

    def handle(self, *args, **options):
        start_time = timezone.now()
        
        if options['verbose']:
            logging.basicConfig(level=logging.INFO)
        
        self.stdout.write(
            self.style.SUCCESS('🚀 Mevzuat scraping başlıyor...')
        )
        
        try:
            # Scraper'ı başlat
            scraper = MevzuatScraper()
            
            # Test modu kontrolü
            if options['test_mode']:
                limit = 5
                self.stdout.write(
                    self.style.WARNING(f'⚠️ TEST MODU - Sadece {limit} mevzuat işlenecek')
                )
            else:
                limit = options['limit']
            
            self.stdout.write(f'📊 İşlenecek maksimum mevzuat sayısı: {limit}')
            
            # 1. Mevzuat listesini çek
            self.stdout.write('📋 Mevzuat listesi çekiliyor...')
            legislation_list = scraper.get_legislation_list()
            
            if not legislation_list:
                raise CommandError('❌ Mevzuat listesi çekilemedi!')
            
            self.stdout.write(
                self.style.SUCCESS(f'✅ {len(legislation_list)} mevzuat bulundu')
            )
            
            # 2. İçerikleri çek ve kaydet
            self.stdout.write(f'📖 İlk {limit} mevzuatın içerikleri çekiliyor...')
            
            processed_count = 0
            saved_count = 0
            error_count = 0
            
            for i, mevzuat in enumerate(legislation_list[:limit], 1):
                try:
                    self.stdout.write(f'[{i}/{min(limit, len(legislation_list))}] {mevzuat.title}')
                    
                    # İçeriği çek
                    mevzuat_with_content = scraper.scrape_legislation_content(mevzuat)
                    
                    # Veritabanına kaydet
                    save_to_database([mevzuat_with_content])
                    
                    processed_count += 1
                    saved_count += 1
                    
                    # Her 10 mevzuattan sonra durum raporu
                    if i % 10 == 0:
                        self.stdout.write(
                            self.style.SUCCESS(f'✅ {i} mevzuat işlendi')
                        )
                    
                except Exception as e:
                    error_count += 1
                    self.stdout.write(
                        self.style.ERROR(f'❌ Hata: {mevzuat.title} - {str(e)}')
                    )
                    continue
            
            # İstatistikler
            end_time = timezone.now()
            duration = (end_time - start_time).total_seconds()
            
            self.stdout.write('\n' + '='*60)
            self.stdout.write(self.style.SUCCESS('🎉 SCRAPING TAMAMLANDI!'))
            self.stdout.write('='*60)
            self.stdout.write(f'📊 İşlenen mevzuat: {processed_count}')
            self.stdout.write(f'✅ Başarılı: {saved_count}')
            self.stdout.write(f'❌ Hatalı: {error_count}')
            self.stdout.write(f'⏱️ Süre: {duration:.1f} saniye')
            self.stdout.write(f'🔗 Admin Panel: https://lexatech.ai/admin/core/professionallegislation/')
            
            # Başarı oranı
            success_rate = (saved_count / processed_count * 100) if processed_count > 0 else 0
            if success_rate >= 90:
                self.stdout.write(self.style.SUCCESS(f'📈 Başarı Oranı: %{success_rate:.1f}'))
            elif success_rate >= 70:
                self.stdout.write(self.style.WARNING(f'📈 Başarı Oranı: %{success_rate:.1f}'))
            else:
                self.stdout.write(self.style.ERROR(f'📈 Başarı Oranı: %{success_rate:.1f}'))
            
        except Exception as e:
            raise CommandError(f'❌ Genel hata: {str(e)}')