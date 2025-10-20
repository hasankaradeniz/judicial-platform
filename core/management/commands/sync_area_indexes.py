from django.core.management.base import BaseCommand
from core.area_based_faiss_manager import AreaBasedFAISSManager
from core.models import JudicialDecision
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Yeni kararları hukuk alanlarına göre indexlere ekler'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=1000, help='İşlenecek maksimum karar sayısı')
        parser.add_argument('--sync-all', action='store_true', help='Tüm kararları senkronize et')
        parser.add_argument('--stats-only', action='store_true', help='Sadece istatistikleri göster')

    def handle(self, *args, **options):
        manager = AreaBasedFAISSManager()
        
        if options['stats_only']:
            self.stdout.write('📊 Alan Bazlı Index İstatistikleri:')
            stats = manager.get_area_index_stats()
            
            total_decisions = 0
            for area, data in stats.items():
                if 'decision_count' in data:
                    count = data['decision_count']
                    size_mb = data['file_size_mb']
                    self.stdout.write(f'  {area}: {count} karar ({size_mb} MB)')
                    total_decisions += count
                    
            self.stdout.write(f'\n📈 Toplam: {total_decisions} karar indexlendi')
            
            # Veritabanı durumu
            db_total = JudicialDecision.objects.count()
            db_processed = JudicialDecision.objects.exclude(detected_legal_area__isnull=True).count()
            
            self.stdout.write(f'\n🗄️  Veritabanı: {db_processed}/{db_total} karar işlendi')
            return
            
        if options['sync_all']:
            self.stdout.write('🔄 Tüm kararları senkronize ediliyor...')
            results = manager.sync_database_with_indexes()
            
            self.stdout.write(f'✅ Senkronizasyon tamamlandı\!')
            self.stdout.write(f'📊 Toplam senkronize edilen: {results["total_synced"]}')
            
            for area, count in results['synced_areas'].items():
                self.stdout.write(f'  {area}: {count} karar')
        else:
            limit = options['limit']
            self.stdout.write(f'🔄 Yeni kararlar işleniyor (limit: {limit})...')
            
            results = manager.process_new_decisions(limit)
            
            self.stdout.write(f'✅ İşlem tamamlandı\!')
            self.stdout.write(f'📊 İşlenen: {results["processed"]} karar')
            self.stdout.write(f'📇 Index\'e eklenen: {results["added_to_index"]} karar')
