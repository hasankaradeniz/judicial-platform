import os
import django
import sys

# Django setup
sys.path.insert(0, '/var/www/judicial_platform')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'judicial_platform.settings')
django.setup()

from core.models import JudicialDecision
from core.area_based_faiss_manager import AreaBasedFAISSManager
from datetime import datetime

print('🔨 Alan bazlı FAISS indeksleri yeniden oluşturuluyor...')
print('📋 1500 karakterden uzun kararlar filtreleniyor...')

# Manager oluştur
manager = AreaBasedFAISSManager()

# Her alan için yeniden oluştur
legal_areas = JudicialDecision.objects.exclude(
    detected_legal_area__isnull=True
).exclude(
    detected_legal_area=''
).filter(
    karar_tam_metni__isnull=False
).exclude(
    karar_tam_metni=''
).values_list('detected_legal_area', flat=True).distinct()

total_processed = 0

for area in legal_areas:
    print(f'\n📁 {area} alanı işleniyor...')
    
    # 1500 karakterden uzun kararları al
    decisions = JudicialDecision.objects.filter(
        detected_legal_area=area,
        karar_tam_metni__isnull=False
    ).exclude(karar_tam_metni='')
    
    filtered_decisions = []
    for decision in decisions:
        if len(decision.karar_tam_metni) >= 1500:
            filtered_decisions.append(decision)
    
    print(f'  ➡️  Toplam: {decisions.count()}, Filtrelenen: {len(filtered_decisions)}')
    
    if filtered_decisions:
        # Bu alanı yeniden oluştur
        success = manager.rebuild_single_area_index(area, filtered_decisions)
        if success:
            total_processed += len(filtered_decisions)
            print(f'  ✅ {area} indeksi oluşturuldu')
        else:
            print(f'  ❌ {area} indeksi oluşturulamadı')

print(f'\n✅ İşlem tamamlandı\! Toplam {total_processed} karar indekslendi.')
