import pandas as pd

# -----------------------------
# 1. CSV Dosyasını Yükle
# -----------------------------
try:
    df = pd.read_csv("Eski_dosyalar/kararlar_etiketli_tamami.csv", encoding="utf-8")
    print("✅ Dosya başarıyla yüklendi.")
except Exception as e:
    print("❌ Dosya yüklenemedi:", e)
    exit()

# -----------------------------
# 2. Beklenen Sütunları Kontrol Et
# -----------------------------
print("\n🔎 Mevcut sütunlar:")
print(df.columns.tolist())

gerekli_sutunlar = {"id", "karar_tam_metni", "hukuk_alani"}
eksik = gerekli_sutunlar - set(df.columns)
if eksik:
    print(f"❌ Eksik sütunlar: {eksik}")
else:
    print("✅ Gerekli tüm sütunlar mevcut.")

# -----------------------------
# 3. Boş Alan Kontrolü
# -----------------------------
bos_alanlar = df["hukuk_alani"].isna().sum()
belirsiz_alanlar = (df["hukuk_alani"].str.lower() == "belirsiz").sum()

print(f"\n📂 Boş etiketli karar sayısı: {bos_alanlar}")
print(f"📂 'belirsiz' olarak etiketlenen karar sayısı: {belirsiz_alanlar}")

# -----------------------------
# 4. Etiket Dağılımı
# -----------------------------
print("\n📊 Etiketlerin dağılımı:")
print(df["hukuk_alani"].value_counts())

# -----------------------------
# 5. Örnek İnceleme
# -----------------------------
print("\n🧾 Rastgele örnek kararlar ve etiketleri:")
sample = df.sample(5, random_state=42)[["karar_tam_metni", "hukuk_alani"]]
for i, row in sample.iterrows():
    print(f"\n📝 Karar Özeti: {row['karar_tam_metni'][:300]}...")
    print(f"🏷️ Etiket: {row['hukuk_alani']}")

# -----------------------------
# 6. Çoklu Etiket Kontrolü
# -----------------------------
df["etiket_sayisi"] = df["hukuk_alani"].str.count(",") + 1
coklu_etiket = (df["etiket_sayisi"] > 1).sum()
print(f"\n🔁 Çoklu etikete sahip karar sayısı: {coklu_etiket}")

# -----------------------------
# 7. Kodlama Kontrolü (Yeniden Dosya Açmayı Dener)
# -----------------------------
try:
    with open("Eski_dosyalar/kararlar_etiketli.csv", encoding="utf-8") as f:
        f.readline()
    print("\n✅ Dosya UTF-8 kodlaması ile sorunsuz okunabiliyor.")
except Exception as e:
    print("\n❌ UTF-8 kodlamasıyla okuma başarısız:", e)

print("\n🎉 Denetleme tamamlandı.")
