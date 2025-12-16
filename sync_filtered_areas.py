import os
import django
import sys
from datetime import datetime

# Django setup
sys.path.insert(0, '/var/www/judicial_platform')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'judicial_platform.settings')
django.setup()

from core.models import JudicialDecision
from core.area_based_faiss_manager import AreaBasedFAISSManager
import time

print('🔨 Alan bazlı FAISS indeksleri oluşturuluyor (1500+ karakter filtreli)...')
print(f'⏰ Başlangıç: {datetime.now()}')

manager = AreaBasedFAISSManager()

# Alan istatistiklerini al
areas = JudicialDecision.objects.exclude(
    detected_legal_area__isnull=True
).exclude(
    detected_legal_area=''
).values_list('detected_legal_area', flat=True).distinct()

print(f'📊 Toplam {len(areas)} alan bulundu')

for area in areas:
    print(f'\n📁 {area} alanı işleniyor...')
    
    # Bu alana ait 1500+ karakter kararları al
    decisions = JudicialDecision.objects.filter(
        detected_legal_area=area
    ).exclude(karar_tam_metni__isnull=True).exclude(karar_tam_metni='')
    
    total_area = decisions.count()
    added = 0
    skipped = 0
    
    start_time = time.time()
    
    for decision in decisions.iterator(chunk_size=1000):
        if len(decision.karar_tam_metni) >= 1500:
            try:
                manager.add_decision_to_area_index(decision.id, area)
                added += 1
            except Exception as e:
                print(f'  ❌ Hata (ID: {decision.id}): {str(e)}')
        else:
            skipped += 1
        
        if (added + skipped) % 5000 == 0:
            elapsed = time.time() - start_time
            speed = (added + skipped) / elapsed if elapsed > 0 else 0
            print(f'  ⏳ İlerleme: {added + skipped}/{total_area} - Eklenen: {added}, Atlanan: {skipped} - Hız: {speed:.0f} karar/sn')
    
    print(f'  ✅ {area} tamamlandı: {added} karar eklendi, {skipped} karar atlandı (<%1500 karakter)')

print(f'\n🎉 Tüm alanlar için indeksleme tamamlandı\!')
print(f'⏰ Bitiş: {datetime.now()}')

# Final istatistikler
stats = manager.get_area_index_stats()
print(f'\n📊 Final İstatistikler:')
for area, count in sorted(stats.items(), key=lambda x: x[1], reverse=True):
    print(f'  - {area}: {count} karar')
