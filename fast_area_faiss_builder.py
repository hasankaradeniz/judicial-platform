#\!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import django
import sys
import time
from datetime import datetime
import faiss
import pickle
import numpy as np
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed

# Django setup
sys.path.insert(0, '/var/www/judicial_platform')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'judicial_platform.settings')
django.setup()

from django.db import connection
from core.models import JudicialDecision
from sentence_transformers import SentenceTransformer

class FastAreaFAISSBuilder:
    def __init__(self):
        self.faiss_dir = "faiss_dizinleri"
        self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        self.batch_size = 5000
        self.min_text_length = 1500
        
    def build_area_index(self, area_name, decisions):
        """Belirli bir alan için FAISS indeksi oluştur"""
        if not decisions:
            return False
            
        print(f"  📝 {len(decisions)} karar için embedding oluşturuluyor...")
        
        # Metinleri hazırla
        texts = []
        valid_ids = []
        
        for decision in decisions:
            if decision['karar_tam_metni'] and len(decision['karar_tam_metni']) >= self.min_text_length:
                text = f"{decision['karar_ozeti'] or ''} {decision['karar_tam_metni'][:2000]}"
                texts.append(text)
                valid_ids.append(decision['id'])
        
        if not texts:
            print(f"  ⚠️ {area_name} için yeterli uzunlukta karar bulunamadı")
            return False
        
        # Embedding oluştur (batch halinde)
        print(f"  🧠 Embedding hesaplanıyor...")
        embeddings = []
        for i in range(0, len(texts), 100):
            batch = texts[i:i+100]
            batch_embeddings = self.model.encode(batch, show_progress_bar=False)
            embeddings.extend(batch_embeddings)
        
        embeddings = np.array(embeddings).astype('float32')
        
        # FAISS indeksi oluştur
        dimension = embeddings.shape[1]
        index = faiss.IndexFlatL2(dimension)
        index.add(embeddings)
        
        # Kaydet
        index_path = os.path.join(self.faiss_dir, f"faiss_{area_name}.index")
        faiss.write_index(index, index_path)
        
        # Mapping dosyasını kaydet
        mapping = {
            'ids': valid_ids,
            'count': len(valid_ids),
            'created_at': datetime.now().isoformat()
        }
        mapping_path = os.path.join(self.faiss_dir, f"mapping_{area_name}.pkl")
        with open(mapping_path, 'wb') as f:
            pickle.dump(mapping, f)
        
        print(f"  ✅ {area_name}: {len(valid_ids)} karar indekslendi")
        return True
    
    def run(self):
        """Tüm alanlar için indeks oluştur"""
        print(f"\n🚀 Hızlı Alan Bazlı FAISS İndeks Oluşturucu")
        print(f"⏰ Başlangıç: {datetime.now()}")
        print(f"📏 Minimum metin uzunluğu: {self.min_text_length} karakter\n")
        
        # Alan istatistiklerini al
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT detected_legal_area, COUNT(*) as count
                FROM core_judicialdecision
                WHERE detected_legal_area IS NOT NULL 
                AND detected_legal_area \!= ''
                AND karar_tam_metni IS NOT NULL
                GROUP BY detected_legal_area
                ORDER BY count DESC
            """)
            area_stats = cursor.fetchall()
        
        print(f"📊 {len(area_stats)} alan bulundu\n")
        
        total_start = time.time()
        success_count = 0
        
        # Her alan için indeks oluştur
        for area_name, count in area_stats:
            print(f"\n{'='*60}")
            print(f"📁 {area_name} işleniyor ({count} karar)...")
            
            area_start = time.time()
            
            # Bu alana ait kararları çek (batch halinde)
            decisions = []
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT id, karar_ozeti, karar_tam_metni
                    FROM core_judicialdecision
                    WHERE detected_legal_area = %s
                    AND karar_tam_metni IS NOT NULL
                    AND LENGTH(karar_tam_metni) >= %s
                """, [area_name, self.min_text_length])
                
                while True:
                    rows = cursor.fetchmany(self.batch_size)
                    if not rows:
                        break
                    for row in rows:
                        decisions.append({
                            'id': row[0],
                            'karar_ozeti': row[1],
                            'karar_tam_metni': row[2]
                        })
            
            # İndeks oluştur
            if self.build_area_index(area_name, decisions):
                success_count += 1
            
            area_time = time.time() - area_start
            print(f"  ⏱️ Süre: {area_time:.1f} saniye")
        
        # Final istatistikler
        total_time = time.time() - total_start
        print(f"\n{'='*60}")
        print(f"\n🎉 İşlem tamamlandı\!")
        print(f"✅ Başarılı: {success_count}/{len(area_stats)} alan")
        print(f"⏱️ Toplam süre: {int(total_time//60)} dakika {int(total_time%60)} saniye")
        print(f"⏰ Bitiş: {datetime.now()}")

if __name__ == "__main__":
    builder = FastAreaFAISSBuilder()
    builder.run()
