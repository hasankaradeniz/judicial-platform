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

def karar_alani_bul(metin, mahkeme):
    metin_lower = metin.lower()
    from collections import defaultdict
    skorlar = defaultdict(int)

    if "anayasa mahkemesi" in mahkeme.lower():
        return ["anayasa_hukuku"]
    if "yargıtay 9. hukuk dairesi" in mahkeme.lower():
        return ["is_hukuku"]

    for alan, kelimeler in alanlar.items():
        for kelime in kelimeler:
            if kelime in metin_lower:
                skorlar[alan.replace(" ", "_")] += 1

    if not skorlar:
        return ["belirsiz"]

    max_skor = max(skorlar.values())
    return [alan for alan, skor in skorlar.items() if skor == max_skor]

# --------------------
# 6. Embedding modeli
# --------------------
model = SentenceTransformer(EMBEDDING_MODEL)

# --------------------
# 7. FAISS Güncelleme
# --------------------
for i, row in tqdm(df.iterrows(), total=len(df), desc="Yeni Kararlar İşleniyor"):
    karar_id = row["id"]
    metin = row["karar_tam_metni"]
    alanlar_listesi = karar_alani_bul(metin, row["karar_veren_mahkeme"])
    embedding = model.encode([metin])

    for alan in alanlar_listesi:
        faiss_path = os.path.join(FAISS_DIR, f"faiss_{alan}.index")
        map_path = os.path.join(FAISS_DIR, f"mapping_{alan}.pkl")

        # FAISS yükle veya oluştur
        if os.path.exists(faiss_path):
            index = faiss.read_index(faiss_path)
        else:
            index = faiss.IndexFlatL2(embedding.shape[1])

        index.add(embedding)

        # Mapping yükle veya oluştur
        if os.path.exists(map_path):
            with open(map_path, "rb") as f:
                mapping = pickle.load(f)
        else:
            mapping = {}

        next_id = max(mapping.keys()) + 1 if mapping else 0
        mapping[next_id] = {
            "mahkeme": row["karar_veren_mahkeme"],
            "esas_no": row["esas_numarasi"],
            "karar_no": row["karar_numarasi"],
            "tarih": row["karar_tarihi"],
            "ozet": row["karar_ozeti"],
            "metin": row["karar_tam_metni"]
        }

        # Kaydet
        faiss.write_index(index, faiss_path)
        with open(map_path, "wb") as f:
            pickle.dump(mapping, f)

# --------------------
# 8. En son işlenen ID'yi kaydet
# --------------------
max_id_in_batch = df["id"].max()
with open(LAST_ID_FILE, "w") as f:
    f.write(str(max_id_in_batch))

print(f"\n✅ Güncelleme tamamlandı. En son işlenen karar ID'si: {max_id_in_batch}")
