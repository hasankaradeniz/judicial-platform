import os
import django
import sys
from datetime import datetime

# Django setup
sys.path.insert(0, '/var/www/judicial_platform')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'judicial_platform.settings')
django.setup()

from core.models import JudicialDecision
from core.legal_area_detector import LegalAreaDetector
from django.db import transaction

print('🎯 Tüm kararlar için hukuk alanı tespiti başlıyor...')
print(f'⏰ Başlangıç: {datetime.now()}')

detector = LegalAreaDetector()
batch_size = 1000

# Tüm kararları al
total = JudicialDecision.objects.count()
print(f'📊 Toplam karar sayısı: {total}')

processed = 0
area_counts = {}

for offset in range(0, total, batch_size):
    batch = JudicialDecision.objects.all().order_by('id')[offset:offset + batch_size]
    
    with transaction.atomic():
        for decision in batch:
            # Özet ve tam metin birleştir
            text_to_analyze = f"{decision.karar_ozeti or ''} {decision.karar_tam_metni[:500] if decision.karar_tam_metni else ''}"
            
            if text_to_analyze.strip():
                # Alan tespiti
                detected_area = detector.get_primary_area(text_to_analyze)
                decision.detected_legal_area = detected_area
                decision.save(update_fields=['detected_legal_area'])
                
                # İstatistik
                area_counts[detected_area] = area_counts.get(detected_area, 0) + 1
            
            processed += 1
    
    if processed % 10000 == 0:
        print(f'✅ {processed}/{total} karar işlendi ({(processed/total)*100:.1f}%)')
        print(f'   📈 Alan dağılımı: {dict(sorted(area_counts.items(), key=lambda x: x[1], reverse=True)[:5])}...')

print(f'\n🎉 İşlem tamamlandı\!')
print(f'⏰ Bitiş: {datetime.now()}')
print(f'\n📊 Final alan dağılımı:')
for area, count in sorted(area_counts.items(), key=lambda x: x[1], reverse=True):
    print(f'  - {area}: {count} karar')
