import psycopg2
import faiss
import pickle
import os
import re
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
import numpy as np
from datetime import datetime

# Veritabanı bağlantısı
conn = psycopg2.connect(
    host="145.223.82.130",
    database="yargi_veri_tabani",
    user="hasankaradeniz",
    password="judicial2024",
    port="5432"
)
cursor = conn.cursor()

# Ayarlar
FAISS_DIR = "faiss_dizinleri"
os.makedirs(FAISS_DIR, exist_ok=True)
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
MIN_TEXT_LENGTH = 1500

print(f"\n🚀 PostgreSQL Alan Bazlı FAISS İndeks Oluşturucu")
print(f"⏰ Başlangıç: {datetime.now()}")
print(f"📏 Minimum metin uzunluğu: {MIN_TEXT_LENGTH} karakter\n")

# Model yükle
print("📦 Embedding modeli yükleniyor...")
model = SentenceTransformer(EMBEDDING_MODEL)

# Alan istatistiklerini al
query = """
    SELECT detected_legal_area, COUNT(*) as count
    FROM core_judicialdecision
    WHERE detected_legal_area IS NOT NULL 
    AND detected_legal_area \!= ''
    AND karar_tam_metni IS NOT NULL
    AND LENGTH(karar_tam_metni) >= %s
    GROUP BY detected_legal_area
    ORDER BY count DESC
"""
cursor.execute(query, (MIN_TEXT_LENGTH,))
area_stats = cursor.fetchall()

print(f"📊 {len(area_stats)} alan bulundu\n")

success_count = 0
total_indexed = 0

# Her alan için indeks oluştur
for area_name, area_count in area_stats:
    print(f"\n{'='*60}")
    print(f"📁 {area_name} işleniyor ({area_count} karar)...")
    
    # Bu alana ait kararları çek
    query = """
        SELECT id, karar_ozeti, karar_tam_metni
        FROM core_judicialdecision
        WHERE detected_legal_area = %s
        AND karar_tam_metni IS NOT NULL
        AND LENGTH(karar_tam_metni) >= %s
        ORDER BY id
    """
    cursor.execute(query, (area_name, MIN_TEXT_LENGTH))
    
    ids = []
    texts = []
    
    # Batch halinde oku
    while True:
        rows = cursor.fetchmany(1000)
        if not rows:
            break
            
        for row in rows:
            id_val, ozet, tam_metin = row
            text = f"{ozet or ''} {tam_metin[:2000]}"
            ids.append(id_val)
            texts.append(text)
    
    if not texts:
        print(f"  ⚠️ {area_name} için yeterli uzunlukta karar bulunamadı")
        continue
    
    print(f"  📝 {len(texts)} karar için embedding oluşturuluyor...")
    
    # Embedding oluştur (batch halinde)
    embeddings = []
    batch_size = 100
    
    for i in tqdm(range(0, len(texts), batch_size), desc="  Embedding"):
        batch = texts[i:i+batch_size]
        batch_embeddings = model.encode(batch, show_progress_bar=False)
        embeddings.extend(batch_embeddings)
    
    embeddings = np.array(embeddings).astype('float32')
    
    # FAISS indeksi oluştur
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)
    
    # İndeksi kaydet
    index_path = os.path.join(FAISS_DIR, f"faiss_{area_name}.index")
    faiss.write_index(index, index_path)
    
    # Mapping dosyasını kaydet
    mapping = {
        'ids': ids,
        'count': len(ids),
        'created_at': datetime.now().isoformat()
    }
    mapping_path = os.path.join(FAISS_DIR, f"mapping_{area_name}.pkl")
    with open(mapping_path, 'wb') as f:
        pickle.dump(mapping, f)
    
    print(f"  ✅ {area_name}: {len(ids)} karar indekslendi")
    success_count += 1
    total_indexed += len(ids)

# Bağlantıyı kapat
cursor.close()
conn.close()

print(f"\n{'='*60}")
print(f"\n🎉 İşlem tamamlandı\!")
print(f"✅ Başarılı: {success_count}/{len(area_stats)} alan")
print(f"📊 Toplam indekslenen: {total_indexed:,} karar")
print(f"⏰ Bitiş: {datetime.now()}")
