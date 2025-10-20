import psycopg2
import faiss
import pickle
import os
import re
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
import pandas as pd

# --------------------
# 1. Veritabanı bağlantısı
# --------------------
conn = psycopg2.connect(
    host="145.223.82.130",
    database="yargi_veri_tabani",
    user="hasankaradeniz",
    password="07072010Dd*",
    port="5432"
)
cursor = conn.cursor()

# --------------------
# 2. Ayarlar
# --------------------
FAISS_DIR = "faiss_dizinleri"
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
LAST_ID_FILE = "last_processed_id.txt"

# --------------------
# 3. Son işlenen ID'yi dosyadan oku
# --------------------
if os.path.exists(LAST_ID_FILE):
    with open(LAST_ID_FILE, "r") as f:
        LAST_PROCESSED_ID = int(f.read().strip())
else:
    LAST_PROCESSED_ID = 261053

print(f"🔍 Veritabanından {LAST_PROCESSED_ID} ID'sinden sonraki kararlar çekiliyor...")

# --------------------
# 4. Yeni kararları çek
# --------------------
query = f"""
    SELECT id, karar_veren_mahkeme, esas_numarasi, karar_numarasi, karar_tarihi,
           karar_ozeti, karar_tam_metni
    FROM core_judicialdecision
    WHERE id > {LAST_PROCESSED_ID} AND karar_tam_metni IS NOT NULL
"""
cursor.execute(query)
rows = cursor.fetchall()
columns = ["id", "karar_veren_mahkeme", "esas_numarasi", "karar_numarasi",
           "karar_tarihi", "karar_ozeti", "karar_tam_metni"]
df = pd.DataFrame(rows, columns=columns)

if df.empty:
    print("✅ Yeni karar bulunamadı. Güncelleme gerekmiyor.")
    exit()

print(f"📄 {len(df)} yeni karar bulundu. İşleniyor...")

# --------------------
# 5. Etiketleme için anahtar kelimeler
# --------------------
alanlar = {}
with open("anahtar_kavramlar.txt", "r", encoding="utf-8") as f:
    lines = [line.strip() for line in f if line.strip()]
    alan = None
    for line in lines:
        if line.startswith("[") and line.endswith("]"):
            alan = line[1:-1].lower()
            alanlar[alan] = set()
        else:
            if alan:
                alanlar[alan].add(line.lower())

# --------------------
# 6. Embedding modeli
# --------------------
model = SentenceTransformer(EMBEDDING_MODEL)

# --------------------
# 7. Önceden FAISS ve Mapping dosyalarını yükleyelim (gerekirse)
# --------------------
faiss_index_dict = {}
mapping_dict = {}

# Tüm embedding'leri topluca encode et
print("🔵 Embedding'ler üretiliyor...")
embeddings = model.encode(df["karar_tam_metni"].tolist(), batch_size=32, show_progress_bar=True)

# --------------------
# 8. FAISS ve Mapping Güncelleme
# --------------------
print("🔵 FAISS dizinleri ve Mapping güncelleniyor...")
for i, row in tqdm(df.iterrows(), total=len(df), desc="Yeni Kararlar İşleniyor"):
    karar_id = row["id"]
    metin = row["karar_tam_metni"]
    embedding = embeddings[i]
    alanlar_listesi = []

    metin_lower = metin.lower()
    from collections import defaultdict
    skorlar = defaultdict(int)

    if "anayasa mahkemesi" in row["karar_veren_mahkeme"].lower():
        alanlar_listesi = ["anayasa_hukuku"]
    elif "yargıtay 9. hukuk dairesi" in row["karar_veren_mahkeme"].lower():
        alanlar_listesi = ["is_hukuku"]
    else:
        for alan, kelimeler in alanlar.items():
            for kelime in kelimeler:
                if kelime in metin_lower:
                    skorlar[alan.replace(" ", "_")] += 1
        if skorlar:
            max_skor = max(skorlar.values())
            alanlar_listesi = [alan for alan, skor in skorlar.items() if skor == max_skor]
        else:
            alanlar_listesi = ["belirsiz"]

    for alan in alanlar_listesi:
        faiss_path = os.path.join(FAISS_DIR, f"faiss_{alan}.index")
        map_path   = os.path.join(FAISS_DIR, f"mapping_{alan}.pkl")

        # FAISS index yükle / oluştur
        if alan not in faiss_index_dict:
            if os.path.exists(faiss_path):
                faiss_index_dict[alan] = faiss.read_index(faiss_path)
            else:
                faiss_index_dict[alan] = faiss.IndexFlatL2(embedding.shape[0])

        # Mapping yükle / oluştur ve eski liste formatını dict'e dönüştür
        if alan not in mapping_dict:
            if os.path.exists(map_path):
                with open(map_path, "rb") as f_map:
                    loaded = pickle.load(f_map)
                if isinstance(loaded, list):
                    # eski liste formatı için: [item0, item1, ...] -> {0: item0, 1: item1, ...}
                    mapping_dict[alan] = {idx: item for idx, item in enumerate(loaded)}
                else:
                    mapping_dict[alan] = loaded
            else:
                mapping_dict[alan] = {}

        # Yeni embedding'i FAISS'e ekle
        faiss_index_dict[alan].add(embedding.reshape(1, -1))

        # Bir sonraki mapping ID'sini hesapla
        if mapping_dict[alan]:
            next_id = max(mapping_dict[alan].keys()) + 1
        else:
            next_id = 0

        mapping_dict[alan][next_id] = {
            "mahkeme": row["karar_veren_mahkeme"],
            "esas_no": row["esas_numarasi"],
            "karar_no": row["karar_numarasi"],
            "tarih": row["karar_tarihi"],
            "ozet": row["karar_ozeti"],
            "metin": row["karar_tam_metni"]
        }

# --------------------
# 9. FAISS ve Mapping'leri topluca kaydet
# --------------------
print("💾 Değişiklikler kaydediliyor...")
for alan, index in faiss_index_dict.items():
    faiss.write_index(index, os.path.join(FAISS_DIR, f"faiss_{alan}.index"))

for alan, mapping in mapping_dict.items():
    with open(os.path.join(FAISS_DIR, f"mapping_{alan}.pkl"), "wb") as f:
        pickle.dump(mapping, f)

# --------------------
# 10. En son işlenen ID'yi kaydet
# --------------------
max_id_in_batch = df["id"].max()
with open(LAST_ID_FILE, "w") as f:
    f.write(str(max_id_in_batch))

print(f"\n✅ Güncelleme tamamlandı. En son işlenen karar ID'si: {max_id_in_batch}")
