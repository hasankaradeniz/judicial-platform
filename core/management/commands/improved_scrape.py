# Geliştirilmiş Django Management Command
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from core.improved_scraper import ImprovedMevzuatScraper, save_to_database

class Command(BaseCommand):
    help = 'Geliştirilmiş mevzuat scraping sistemi'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=10,
            help='Kaç mevzuat işlenecek (varsayılan: 10)'
        )
        parser.add_argument(
            '--search',
            type=str,
            default='',
            help='Arama terimi'
        )

    def handle(self, *args, **options):
        start_time = timezone.now()
        limit = options['limit']
        search_term = options['search']
        
        self.stdout.write(
            self.style.SUCCESS('🚀 Geliştirilmiş mevzuat scraping başlıyor...')
        )
        
        try:
            scraper = ImprovedMevzuatScraper()
            
            # Mevzuat listesini çek
            self.stdout.write('📋 Mevzuat listesi çekiliyor...')
            legislation_list = scraper.get_legislation_by_direct_search(search_term)
            
            if not legislation_list:
                self.stdout.write(
                    self.style.ERROR('⚠️ Canlı scraping başarısız, bilinen mevzuat listesi kullanılıyor')
                )
                legislation_list = scraper._get_known_legislation_list()
            
            self.stdout.write(
                self.style.SUCCESS(f'✅ {len(legislation_list)} mevzuat bulundu')
            )
            
            # İçerikleri çek
            processed_count = 0
            for i, mevzuat in enumerate(legislation_list[:limit], 1):
                self.stdout.write(f'[{i}/{min(limit, len(legislation_list))}] {mevzuat.title}')
                
                try:
                    mevzuat_with_content = scraper.scrape_legislation_content(mevzuat)
                    legislation_list[i-1] = mevzuat_with_content
                    processed_count += 1
                    
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f'⚠️ İçerik hatası: {str(e)}')
                    )
            
            # Veritabanına kaydet
            self.stdout.write('💾 Veritabanına kaydediliyor...')
            save_to_database(legislation_list[:processed_count])
            
            # Sonuç
            end_time = timezone.now()
            duration = (end_time - start_time).total_seconds()
            
            self.stdout.write('\n' + '='*50)
            self.stdout.write(self.style.SUCCESS('🎉 İŞLEM TAMAMLANDI!'))
            self.stdout.write('='*50)
            self.stdout.write(f'📊 İşlenen mevzuat: {processed_count}')
            self.stdout.write(f'⏱️ Süre: {duration:.1f} saniye')
            self.stdout.write(f'🔗 Kontrol: https://lexatech.ai/professional-legislation/')
            
        except Exception as e:
            raise CommandError(f'❌ Genel hata: {str(e)}')