import os
from core.models import HukukKategorisi, KararKategoriIliskisi
from django.db.models import Count

print('=== MEVCUT FAISS DURUMU ===')

# FAISS dosyalarını kontrol et
faiss_dir = '/var/www/judicial_platform/faiss_dizinleri'
if os.path.exists(faiss_dir):
    files = [f for f in os.listdir(faiss_dir) if f.endswith('.index')]
    print(f'Mevcut FAISS index dosyaları ({len(files)} adet):')
    for f in files:
        size_mb = os.path.getsize(os.path.join(faiss_dir, f)) / (1024*1024)
        print(f'  - {f}: {size_mb:.1f} MB')

print('\n=== HİYERARŞİK KATEGORİ ANALİZİ ===')

# Ana kategoriler
ana_kategoriler = HukukKategorisi.objects.values('ana_kategori').annotate(
    kategori_sayisi=Count('id'),
    karar_sayisi=Count('kararkategoriiliskisi')
).order_by('-karar_sayisi')

print('Ana kategoriler ve karar sayıları:')
for kat in ana_kategoriler:
    print(f'  {kat["ana_kategori"]}: {kat["karar_sayisi"]:,} karar, {kat["kategori_sayisi"]} alt kategori')

print('\n=== ÖNCEDEN FAISS YAPILMIŞ ALANLAR ===')

# Hangi alanlar için zaten FAISS var
existing_areas = []
for f in files:
    if 'faiss_' in f:
        area = f.replace('faiss_', '').replace('.index', '')
        existing_areas.append(area)

print('Mevcut FAISS alanları:')
for area in existing_areas:
    print(f'  - {area}')

print('\n=== HİYERARŞİK KATEGORİ ÖNERİSİ ===')

# En çok kararı olan hiyerarşik kategoriler
top_hierarchical = HukukKategorisi.objects.filter(
    kod__isnull=False
).annotate(
    karar_sayisi=Count('kararkategoriiliskisi')
).filter(karar_sayisi__gt=1000).order_by('-karar_sayisi')[:15]

print('FAISS için öncelikli hiyerarşik kategoriler (>1000 karar):')
for kat in top_hierarchical:
    print(f'  {kat.kod}: {kat.get_full_hierarchy()} ({kat.karar_sayisi:,} karar)')
