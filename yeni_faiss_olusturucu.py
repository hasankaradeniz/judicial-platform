import psycopg2
import faiss
import pickle
import os
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
import pandas as pd

# --- 1. Veritabanı bağlantısı ---
conn = psycopg2.connect(
    host="145.223.82.130",
    database="yargi_veri_tabani",
    user="hasankaradeniz",
    password="07072010Dd*",
    port="5432"
)
cursor = conn.cursor()

# --- 2. Ayarlar ---
FAISS_DIR = "faiss_dizinleri"
os.makedirs(FAISS_DIR, exist_ok=True)
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
LAST_ID_FILE = "last_processed_id.txt"

# --- 3. Son işlenen ID'yi dosyadan oku ---
if os.path.exists(LAST_ID_FILE):
    with open(LAST_ID_FILE, "r") as f:
        LAST_PROCESSED_ID = int(f.read().strip())
else:
    LAST_PROCESSED_ID = 0  # ilk kez çalışacaksa 0

print(f"\n🔍 {LAST_PROCESSED_ID} ID'sinden sonraki kararlar çekiliyor...")

# --- 4. Yeni kararları çek ---
query = f"""
    SELECT id, karar_veren_mahkeme, esas_numarasi, karar_numarasi, karar_tarihi,
           karar_ozeti, karar_tam_metni
    FROM core_judicialdecision
    WHERE id > {LAST_PROCESSED_ID} AND karar_tam_metni IS NOT NULL
    ORDER BY id
"""
cursor.execute(query)
rows = cursor.fetchall()
columns = ["id", "karar_veren_mahkeme", "esas_numarasi", "karar_numarasi",
           "karar_tarihi", "karar_ozeti", "karar_tam_metni"]
df = pd.DataFrame(rows, columns=columns)

if df.empty:
    print("✅ Yeni karar bulunamadı. Güncelleme gerekmiyor.")
    exit()

print(f"\n📄 {len(df)} yeni karar bulundu. İşleniyor...")

# --- 5. Etiketleme için anahtar kelimeler yükleniyor ---
alanlar = {}
with open("anahtar_kavramlar.txt", "r", encoding="utf-8") as f:
    lines = [line.strip() for line in f if line.strip()]
    alan = None
    for line in lines:
        if line.startswith("[") and line.endswith("]"):
            alan = line[1:-1].lower().replace(" ", "_")
            alanlar[alan] = set()
        else:
            if alan:
                alanlar[alan].add(line.lower())

# --- 6. Embedding modeli yükleniyor ---
model = SentenceTransformer(EMBEDDING_MODEL)

# --- 7. FAISS ve Mapping dosyalarını yükle/güncelle ---
faiss_index_dict = {}
mapping_dict = {}

# --- 8. Embedding üret ---
print("🔵 Embedding'ler üretiliyor...")
embeddings = model.encode(df["karar_tam_metni"].tolist(), batch_size=32, show_progress_bar=True, normalize_embeddings=True)

# --- 9. Kararları alanlara etiketle ve FAISS/MAPPING'e ekle ---
from collections import defaultdict

print("🔵 FAISS dizinleri ve Mapping güncelleniyor...")
for idx, row in tqdm(df.iterrows(), total=len(df), desc="Yeni Kararlar"):
    karar_id = int(row["id"])
    metin = row["karar_tam_metni"] or ""
    mahkeme = (row["karar_veren_mahkeme"] or "").lower()
    ozet = row["karar_ozeti"]
    embedding = embeddings[idx]
    alanlar_listesi = []

    # 1. Mahkeme ismine göre önceliklendirilmiş hızlı alan tayini (geliştirilebilir!)
    if "anayasa mahkemesi" in mahkeme:
        alanlar_listesi = ["anayasa_hukuku"]
    elif "yargıtay 9. hukuk" in mahkeme:
        alanlar_listesi = ["is_hukuku"]
    elif "yargıtay 11. hukuk" in mahkeme:
        alanlar_listesi = ["ticaret_hukuku"]
    else:
        # 2. Anahtar kelimelerle skor tabanlı etiketleme
        skorlar = defaultdict(int)
        metin_lower = metin.lower()
        for alan, kelimeler in alanlar.items():
            for kelime in kelimeler:
                if kelime in metin_lower:
                    skorlar[alan] += 1
        if skorlar:
            max_skor = max(skorlar.values())
            alanlar_listesi = [alan for alan, skor in skorlar.items() if skor == max_skor and skor > 0]
        else:
            alanlar_listesi = ["belirsiz"]

    # Her alana ayrı ekle (bir karar çok alana giriyorsa, her FAISS + mapping'e eklenir)
    for alan in set(alanlar_listesi):
        faiss_path = os.path.join(FAISS_DIR, f"faiss_{alan}.index")
        map_path = os.path.join(FAISS_DIR, f"mapping_{alan}.pkl")

        # FAISS indexi yükle veya oluştur
        if alan not in faiss_index_dict:
            if os.path.exists(faiss_path):
                faiss_index_dict[alan] = faiss.read_index(faiss_path)
            else:
                faiss_index_dict[alan] = faiss.IndexFlatL2(embedding.shape[0])

        # Mapping list olarak yükle veya oluştur
        if alan not in mapping_dict:
            if os.path.exists(map_path):
                with open(map_path, "rb") as f:
                    mapping_dict[alan] = pickle.load(f)
            else:
                mapping_dict[alan] = []

        # FAISS indexe ekle
        faiss_index_dict[alan].add(embedding.reshape(1, -1))
        # Mapping listesine ekle
        mapping_dict[alan].append({
            "karar_id": karar_id,
            "mahkeme": row["karar_veren_mahkeme"],
            "esas_no": row["esas_numarasi"],
            "karar_no": row["karar_numarasi"],
            "tarih": str(row["karar_tarihi"]),
            "ozet": ozet,
            "metin": metin
        })

# --- 10. FAISS ve Mapping'leri kaydet ---
print("\n💾 Değişiklikler kaydediliyor...")
for alan, index in faiss_index_dict.items():
    faiss.write_index(index, os.path.join(FAISS_DIR, f"faiss_{alan}.index"))
for alan, mapping in mapping_dict.items():
    with open(os.path.join(FAISS_DIR, f"mapping_{alan}.pkl"), "wb") as f:
        pickle.dump(mapping, f)

# --- 11. En son işlenen ID'yi kaydet ---
max_id_in_batch = int(df["id"].max())
with open(LAST_ID_FILE, "w") as f:
    f.write(str(max_id_in_batch))

print(f"\n✅ FAISS güncelleme tamamlandı. En son işlenen karar ID'si: {max_id_in_batch}")

