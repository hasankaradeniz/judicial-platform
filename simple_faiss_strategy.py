from core.models import HukukKategorisi, KararKategoriIliskisi, JudicialDecision
from django.db.models import Count

print('=== FAISS YENİDEN OLUŞTURMA STRATEJİSİ ===')

# Kritik kategoriler (>20K karar)
print('\n🚀 ÖNCELİKLİ KATEGORİLER (>20K karar):')
kritik = HukukKategorisi.objects.filter(kod__isnull=False).annotate(
    karar_sayisi=Count('kararkategoriiliskisi')
).filter(karar_sayisi__gte=20000).order_by('-karar_sayisi')

for i, kat in enumerate(kritik, 1):
    size_mb = kat.karar_sayisi * 2 / 1000  # Rough estimate
    priority = '⭐⭐⭐' if kat.karar_sayisi > 100000 else '⭐⭐'
    print(f'  {priority} {i:2d}. {kat.kod}: {kat.karar_sayisi:,} karar (~{size_mb:.1f} MB)')
    print(f'       {kat.get_full_hierarchy()}')

# Multi-category analizi
print('\n🔀 MULTI-CATEGORY ANALİZİ:')
multi_decisions = JudicialDecision.objects.annotate(
    kategori_sayisi=Count('kararkategoriiliskisi')
).filter(kategori_sayisi__gt=1)

multi_count = multi_decisions.count()
total_decisions = JudicialDecision.objects.count()
print(f'  Multi-category kararlar: {multi_count:,} / {total_decisions:,} ({(multi_count/total_decisions)*100:.1f}%)')

print('\n💿 UYGULAMA ÖNCELİĞİ:')
print('1. OH_MH_BH_DS (462K karar) - Borçlar Hukuku')
print('2. KH_IH_IYH (174K karar) - İdari Yargılama') 
print('3. KH_CH + KH_CMH (~210K karar) - Ceza Hukuku')
print('4. KH_VH (69K karar) - Vergi Hukuku')
print('5. Multi-category hybrid index')
