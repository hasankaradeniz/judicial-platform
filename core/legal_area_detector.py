"""
Hukuk Alanı Tespit Sistemi - Kullanıcı sorgusundan hukuk alanını belirler
"""
import re
from typing import List, Dict, Tuple
from collections import Counter

class LegalAreaDetector:
    def __init__(self):
        self.area_keywords = {
            'aile_hukuku': [
                'boşanma', 'evlilik', 'nafaka', 'velayet', 'çocuk', 'eş',
                'karı', 'koca', 'nişan', 'düğün', 'evlat', 'aile', 'ana', 'baba',
                'çeyiz', 'mehir', 'miras payı', 'aile konutu', 'aile şirketi'
            ],
            'borclar_hukuku': [
                'sözleşme', 'kira', 'satış', 'borç', 'alacak', 'tazminat',
                'sigorta', 'hasar', 'kaza', 'sorumluluk', 'zarar', 'ödeme',
                'fatura', 'kredi', 'çek', 'senet', 'keşide', 'ciro'
            ],
            'is_hukuku': [
                'işçi', 'işveren', 'çalışan', 'maaş', 'ücret', 'fazla mesai',
                'kıdem', 'ihbar', 'işten çıkarma', 'mobbing', 'iş kazası',
                'sendika', 'toplu sözleşme', 'grev', 'lokavt', 'izin'
            ],
            'vergi_hukuku': [
                'vergi', 'gelir vergisi', 'kurumlar vergisi', 'kdv', 'mtv',
                'stopaj', 'tevkifat', 'beyanname', 'matrah', 'tarh', 'tahsil',
                'vergi dairesi', 'mükellef', 'mali', 'muhasebe'
            ],
            'idare_hukuku': [
                'belediye', 'valilik', 'kaymakamlık', 'ruhsat', 'izin',
                'imar', 'istimlak', 'kamulaştırma', 'devlet', 'kamu',
                'memur', 'görevli', 'kamu yararı', 'kamu düzeni'
            ],
            'icra_ve_iflas_hukuku': [
                'icra', 'iflas', 'haciz', 'takip', 'borçlu', 'alacaklı',
                'konkordato', 'ödeme emri', 'itiraz', 'şikayyet', 'satış'
            ],
            'ticaret_hukuku': [
                'şirket', 'ortaklık', 'anonim', 'limited', 'kollektif',
                'komandit', 'ticaret sicili', 'ticari', 'işletme', 'firma',
                'mağaza', 'dükkan', 'esnaf', 'sanayici', 'müteahhit'
            ],
            'ceza_hukuku': [
                'suç', 'ceza', 'hapis', 'para cezası', 'hırsızlık', 'dolandırıcılık',
                'yaralama', 'tehdit', 'hakaret', 'rüşvet', 'savcı', 'mahkeme'
            ],
            'anayasa_hukuku': [
                'anayasa', 'temel hak', 'özgürlük', 'eşitlik', 'adalet',
                'hak', 'demokrasi', 'seçim', 'siyasi parti', 'meclis'
            ],
            'sosyal_guvenlik_hukuku': [
                'sgk', 'emekli', 'emeklilik', 'prim', 'sigorta', 'sağlık',
                'bağkur', 'ssk', 'işsizlik', 'analık', 'malullük'
            ]
        }
        
        # Index dosya isimlerini normalize et
        self.available_areas = [
            'aile_hukuku', 'anayasa_hukuku', 'belediye_hukuku', 'borclar_hukuku',
            'cevre_hukuku', 'danistay_sgk', 'danistay_vergi', 'deniz_ticaret_hukuku',
            'enerji_maden', 'esya_hukuku', 'icra_ve_iflas_hukuku', 'idare_hukuku',
            'is_hukuku', 'kamu_gorevlisi_hukuku', 'kamu_ihale_hukuku',
            'kamulastirma_hukuku', 'kisiler_hukuku', 'kiymetli_evrak',
            'miras_hukuku', 'sigorta_hukuku', 'sirketler_hukuku',
            'sosyal_guvenlik_hukuku', 'ticaret_hukuku', 'ticari_isletme',
            'vergi_hukuku', 'yabancilar_ve_vatandaslik', 'yuksekogretim_hukuku'
        ]
    
    def detect_legal_area(self, query: str) -> List[Tuple[str, float]]:
        """
        Sorgudan hukuk alanlarını tespit eder
        Returns: [(alan_adi, confidence_score), ...]
        """
        query = query.lower().strip()
        scores = {}
        
        for area, keywords in self.area_keywords.items():
            score = 0
            for keyword in keywords:
                if keyword.lower() in query:
                    # Tam kelime eşleşmesi daha yüksek puan
                    if re.search(r'\b' + re.escape(keyword.lower()) + r'\b', query):
                        score += 2
                    else:
                        score += 1
            
            if score > 0:
                scores[area] = score / len(keywords)  # Normalize
        
        # En yüksek skorlu alanları döndür
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_scores
    
    def get_primary_area(self, query: str) -> str:
        """Ana hukuk alanını döndürür"""
        areas = self.detect_legal_area(query)
        if areas:
            primary = areas[0][0]
            # Mevcut indexlerde var mı kontrol et
            if primary in self.available_areas:
                return primary
            # Yakın eşleşme ara
            for area in self.available_areas:
                if primary in area or area in primary:
                    return area
        
        # Varsayılan olarak en büyük index'i döndür
        return 'idare_hukuku'
    
    def get_multiple_areas(self, query: str, threshold: float = 0.1) -> List[str]:
        """Threshold üzeri tüm alanları döndürür"""
        areas = self.detect_legal_area(query)
        return [area for area, score in areas if score >= threshold]

