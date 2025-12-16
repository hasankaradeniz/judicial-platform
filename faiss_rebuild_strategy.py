#\!/usr/bin/env python3
"""
Hiyerarşik Multi-Kategori FAISS Yeniden Oluşturma Stratejisi
Bu script, mevcut kategori sistemine göre optimal FAISS yapısını oluşturur
"""

import os
from core.models import HukukKategorisi, KararKategoriIliskisi, JudicialDecision
from django.db.models import Count, Q

class HierarchicalFAISSBuilder:
    def __init__(self):
        self.base_path = '/var/www/judicial_platform/faiss_hierarchical'
        self.ensure_directories()
    
    def ensure_directories(self):
        """Dizin yapısını oluştur"""
        dirs = [
            f'{self.base_path}/ana_kategoriler',
            f'{self.base_path}/alt_alanlar', 
            f'{self.base_path}/hybrid',
            f'{self.base_path}/backup'
        ]
        for d in dirs:
            os.makedirs(d, exist_ok=True)
    
    def analyze_rebuild_priority(self):
        """Yeniden oluşturma önceliğini analiz et"""
        
        print('=== FAISS YENİDEN OLUŞTURMA STRATEJİSİ ===\n')
        
        # 1. Ana Kategoriler
        print('🎯 FAZ 1: ANA KATEGORİLER')
        ana_kategoriler = HukukKategorisi.objects.values('ana_kategori').annotate(
            karar_sayisi=Count('kararkategoriiliskisi', distinct=True)
        ).order_by('-karar_sayisi')
        
        for kat in ana_kategoriler:
            size_mb = kat['karar_sayisi'] * 2 / 1000  # Rough estimate
            print(f'  📂 {kat["ana_kategori"]}: {kat["karar_sayisi"]:,} karar (~{size_mb:.1f} MB)')
        
        # 2. Kritik Alt Kategoriler (>20K karar)
        print('\n🚀 FAZ 2: KRİTİK ALT KATEGORİLER (>20K karar)')
        kritik_kategoriler = HukukKategorisi.objects.filter(
            kod__isnull=False
        ).annotate(
            karar_sayisi=Count('kararkategoriiliskisi')
        ).filter(karar_sayisi__gte=20000).order_by('-karar_sayisi')
        
        total_critical_size = 0
        for i, kat in enumerate(kritik_kategoriler, 1):
            size_mb = kat.karar_sayisi * 2 / 1000
            total_critical_size += size_mb
            priority = '⭐⭐⭐' if kat.karar_sayisi > 100000 else '⭐⭐' if kat.karar_sayisi > 50000 else '⭐'
            print(f'  {priority} {i:2d}. {kat.kod}: {kat.get_full_hierarchy()[:60]}... ({kat.karar_sayisi:,} karar, ~{size_mb:.1f} MB)')
        
        # 3. Orta Öncelik (5K-20K karar)
        print('\n📊 FAZ 3: ORTA ÖNCELİK (5K-20K karar)')
        orta_kategoriler = HukukKategorisi.objects.filter(
            kod__isnull=False
        ).annotate(
            karar_sayisi=Count('kararkategoriiliskisi')
        ).filter(karar_sayisi__gte=5000, karar_sayisi__lt=20000).order_by('-karar_sayisi')
        
        total_medium_size = 0
        for kat in orta_kategoriler[:10]:  # İlk 10'u göster
            size_mb = kat.karar_sayisi * 2 / 1000
            total_medium_size += size_mb
            print(f'    📁 {kat.kod}: {kat.get_full_hierarchy()[:50]}... ({kat.karar_sayisi:,} karar)')
        
        if orta_kategoriler.count() > 10:
            print(f'    ... ve {orta_kategoriler.count() - 10} kategori daha')
        
        # 4. Multi-Category Analizi
        print('\n🔀 FAZ 4: MULTI-CATEGORY ANALİZİ')
        
        # Birden fazla kategorisi olan kararlar
        multi_category_decisions = JudicialDecision.objects.annotate(
            kategori_sayisi=Count('kararkategoriiliskisi')
        ).filter(kategori_sayisi__gt=1)
        
        multi_count = multi_category_decisions.count()
        total_decisions = JudicialDecision.objects.count()
        multi_percentage = (multi_count / total_decisions) * 100
        
        print(f'  🔀 Multi-category kararlar: {multi_count:,} / {total_decisions:,} ({multi_percentage:.1f}%)')
        
        # En çok kategorisi olan kararlar
        top_multi = multi_category_decisions.order_by('-kategori_sayisi')[:5]
        for karar in top_multi:
            print(f'    📋 ID {karar.id}: {karar.kategori_sayisi} kategori')
        
        # 5. Disk Alanı Tahmini
        print('\n💾 DİSK ALANI TAHMİNİ')
        print(f'  📊 Kritik kategoriler: ~{total_critical_size:.1f} MB')
        print(f'  📊 Orta kategoriler: ~{total_medium_size:.1f} MB')
        print(f'  📊 Ana kategoriler: ~{(ana_kategoriler[0]["karar_sayisi"] + ana_kategoriler[1]["karar_sayisi"]) * 2 / 1000:.1f} MB')
        print(f'  📊 Multi-category hybrid: ~{multi_count * 2 / 1000:.1f} MB')
        total_estimated = total_critical_size + total_medium_size + 2000 + (multi_count * 2 / 1000)
        print(f'  💿 TOPLAM TAHMİN: ~{total_estimated:.1f} MB (~{total_estimated/1000:.1f} GB)')
        
        print('\n' + '='*80)
        print('ÖNERİLEN UYGULAMA SIRASI:')
        print('1. 🚀 OH_MH_BH_DS (462K karar) - En kritik, günlük kullanım')
        print('2. 🚀 KH_IH_IYH (174K karar) - İdari yargı, sık kullanım') 
        print('3. 🚀 KH_CH + KH_CMH (212K karar) - Ceza hukuku paketi')
        print('4. 📊 KAMU_HUKUKU ana kategorisi (491K karar)')
        print('5. 📊 OZEL_HUKUK ana kategorisi (474K karar)')
        print('6. 🔀 Multi-category hybrid index')
        print('='*80)
        
        return {
            'kritik_kategoriler': kritik_kategoriler,
            'orta_kategoriler': orta_kategoriler,
            'multi_category_count': multi_count,
            'total_size_estimate': total_estimated
        }

if __name__ == '__main__':
    builder = HierarchicalFAISSBuilder()
    strategy = builder.analyze_rebuild_priority()
