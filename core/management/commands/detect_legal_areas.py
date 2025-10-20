from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import JudicialDecision
from core.legal_area_detector import LegalAreaDetector
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Tüm kararlar için hukuk alanı tespiti yapar'

    def add_arguments(self, parser):
        parser.add_argument('--batch-size', type=int, default=1000, help='Batch boyutu')
        parser.add_argument('--start-id', type=int, default=1, help='Başlangıç ID')
        parser.add_argument('--limit', type=int, help='İşlenecek maksimum karar sayısı')
        parser.add_argument('--dry-run', action='store_true', help='Sadece test, kaydetme')

    def handle(self, *args, **options):
        batch_size = options['batch_size']
        start_id = options['start_id']
        limit = options['limit']
        dry_run = options['dry_run']
        
        detector = LegalAreaDetector()
        
        # Query oluştur
        queryset = JudicialDecision.objects.filter(
            id__gte=start_id,
            detected_legal_area__isnull=True
        ).order_by('id')
        
        if limit:
            queryset = queryset[:limit]
            
        total = queryset.count()
        self.stdout.write(f'🎯 Toplam işlenecek karar: {total}')
        
        if dry_run:
            self.stdout.write('⚠️  DRY RUN modu - değişiklikler kaydedilmeyecek')
        
        processed = 0
        updated = 0
        
        # Batch'ler halinde işle
        for offset in range(0, total, batch_size):
            batch = queryset[offset:offset + batch_size]
            
            with transaction.atomic():
                for decision in batch:
                    try:
                        # Metin hazırla
                        text = (decision.karar_ozeti or '') + ' ' + (decision.karar_tam_metni or '')
                        if len(text.strip()) < 10:
                            continue
                            
                        # Hukuk alanı tespit et
                        legal_area = detector.get_primary_area(text)
                        
                        if not dry_run:
                            decision.detected_legal_area = legal_area
                            decision.save(update_fields=['detected_legal_area'])
                            updated += 1
                        else:
                            self.stdout.write(f'  ID {decision.id}: {legal_area}')
                            
                        processed += 1
                        
                        if processed % 100 == 0:
                            self.stdout.write(f'⏳ İşlenen: {processed}/{total} | Güncellenen: {updated}')
                            
                    except Exception as e:
                        logger.error(f'Error processing decision {decision.id}: {e}')
                        continue
        
        self.stdout.write(f'✅ Tamamlandı\!')
        self.stdout.write(f'📊 İşlenen: {processed}')
        if not dry_run:
            self.stdout.write(f'💾 Güncellenen: {updated}')
        
        # İstatistikler
        if not dry_run:
            area_stats = {}
            for decision in JudicialDecision.objects.exclude(detected_legal_area__isnull=True):
                area = decision.detected_legal_area
                area_stats[area] = area_stats.get(area, 0) + 1
            
            self.stdout.write('\n📈 Hukuk Alanı Dağılımı:')
            for area, count in sorted(area_stats.items(), key=lambda x: x[1], reverse=True)[:10]:
                self.stdout.write(f'  {area}: {count} karar')
