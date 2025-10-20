# 🚀 Mevzuat Scraping Sistemi

Bu sistem **mevzuat.gov.tr** sitesinden otomatik olarak mevzuat verilerini çekerek veritabanına kaydetmek için tasarlanmıştır.

## 📋 Özellikler

### ✨ 3 Farklı Scraping Yöntemi
1. **🔍 Selenium Scraping** (`scrape_mevzuat.py`)
2. **📡 API/RSS Scraping** (`mevzuat_api_scraper.py`) 
3. **⏰ Zamanlanmış Scraping** (`mevzuat_scheduler.py`)

### 🎯 Ana İşlevler
- **Akıllı Veri Çıkarma**: Başlık, numara, tarih, tam metin
- **Çoklu Format Desteği**: RSS, XML, HTML parsing
- **Hata Toleransı**: Robust error handling
- **Rate Limiting**: Site yükünü minimize etme
- **Duplicate Detection**: Tekrar eden verileri engelleme
- **Real-time Statistics**: Canlı istatistik takibi

## 🚀 Kurulum

### 1. Gerekli Paketleri Yükle
```bash
pip install -r requirements.txt
```

### 2. Chrome Driver Kurulumu
Sistem otomatik olarak ChromeDriver'ı yükler, ancak manuel kurulum da yapabilirsiniz:
```bash
# macOS
brew install chromedriver

# Ubuntu
sudo apt-get install chromium-chromedriver

# Windows - ChromeDriver'ı PATH'e ekleyin
```

## 📖 Kullanım Kılavuzu

### 🔍 1. Selenium ile Detaylı Scraping

```bash
# Temel kullanım
python manage.py scrape_mevzuat

# Gelişmiş parametreler
python manage.py scrape_mevzuat \
    --start-page 1 \
    --max-pages 5 \
    --kategori kanun \
    --test-mode \
    --headless \
    --delay 2.0
```

**Parametreler:**
- `--start-page`: Başlangıç sayfa numarası (varsayılan: 1)
- `--max-pages`: Maksimum sayfa sayısı (varsayılan: 10)
- `--kategori`: Mevzuat türü filtresi (kanun, kararname, yonetmelik, tuzuk, teblig, genelge)
- `--test-mode`: Test modu (sadece 3 mevzuat çeker)
- `--headless`: Tarayıcıyı görünmez modda çalıştır
- `--delay`: İstekler arası bekleme süresi (saniye)

### 📡 2. API/RSS ile Hızlı Scraping

```bash
# RSS ile hızlı güncelleme
python manage.py mevzuat_api_scraper --method rss --limit 100

# API endpoint testi
python manage.py mevzuat_api_scraper --method api --limit 50

# Sitemap tarama
python manage.py mevzuat_api_scraper --method sitemap --limit 200

# Son 7 günün mevzuatları
python manage.py mevzuat_api_scraper \
    --method rss \
    --limit 100 \
    --days-back 7 \
    --update-existing
```

**Parametreler:**
- `--method`: Scraping yöntemi (rss, api, sitemap)
- `--limit`: Maksimum çekilecek mevzuat sayısı
- `--days-back`: Kaç gün öncesine kadar çek
- `--update-existing`: Mevcut kayıtları da güncelle

### ⏰ 3. Zamanlanmış Otomatik Scraping

```bash
# Günlük 02:00'da çalıştır
python manage.py mevzuat_scheduler --mode daily --time "02:00"

# Haftalık pazartesi 03:00'da
python manage.py mevzuat_scheduler --mode weekly --time "03:00"

# Saatlik çalıştır
python manage.py mevzuat_scheduler --mode hourly

# Tek seferlik çalıştır
python manage.py mevzuat_scheduler --mode once

# Email bildirimleri ile
python manage.py mevzuat_scheduler \
    --mode daily \
    --time "02:00" \
    --email-notifications \
    --max-errors 3
```

**Parametreler:**
- `--mode`: Çalışma modu (once, daily, weekly, hourly)
- `--time`: Günlük çalışma saati (HH:MM)
- `--email-notifications`: Email bildirimleri gönder
- `--max-errors`: Maksimum hata sayısı

## 📊 İstatistik ve Monitoring

### Canlı İstatistikler
Scraping sırasında şu istatistikler gösterilir:
- ✅ Yeni eklenen mevzuat sayısı
- 🔄 Güncellenen mevzuat sayısı
- ⏭️ Atlanan kayıt sayısı
- ❌ Hata sayısı
- ⏱️ Toplam süre
- 🎯 Başarı oranı

### Veritabanı Logları
Tüm işlemler `MevzuatLog` modelinde loglanır:
```python
# Son 10 log kaydını görüntüle
from core.models import MevzuatLog
logs = MevzuatLog.objects.order_by('-olusturma_tarihi')[:10]
for log in logs:
    print(f"{log.olusturma_tarihi}: {log.islem_turu} - {log.aciklama}")
```

## ⚡ Performans Optimizasyonu

### Hızlı Güncelleme İçin
```bash
# Sadece RSS ile son 3 günün mevzuatları
python manage.py mevzuat_api_scraper \
    --method rss \
    --limit 50 \
    --days-back 3
```

### Detaylı Analiz İçin
```bash
# Selenium ile kategori bazlı
python manage.py scrape_mevzuat \
    --kategori kanun \
    --max-pages 10 \
    --delay 1.0
```

## 🛠️ Troubleshooting

### Yaygın Hatalar ve Çözümleri

**1. ChromeDriver Hatası**
```bash
# ChromeDriver'ı manuel yükle
pip install webdriver-manager
```

**2. Selenium Timeout Hatası**
```bash
# Daha uzun delay kullan
python manage.py scrape_mevzuat --delay 5.0
```

**3. Memory Hatası**
```bash
# Daha az sayfa işle
python manage.py scrape_mevzuat --max-pages 3 --test-mode
```

**4. Site Bloklama**
```bash
# User-agent ve delay değiştir
python manage.py scrape_mevzuat --delay 10.0 --headless
```

### Log Dosyaları
- `mevzuat_scheduler.log`: Scheduler logları
- Django admin panelinden `MevzuatLog` tablosunu kontrol edin

## 📈 Önerilen Kullanım Stratejisi

### 🎯 Günlük Rutin
```bash
# Sabah 02:00'da otomatik RSS güncellemesi
python manage.py mevzuat_scheduler --mode daily --time "02:00"
```

### 📅 Haftalık Detaylı Tarama
```bash
# Pazartesi 03:00'da detaylı scraping
python manage.py scrape_mevzuat --max-pages 20 --delay 3.0
```

### 🚨 Acil Güncellemeler
```bash
# Hızlı RSS taraması
python manage.py mevzuat_api_scraper --method rss --limit 200 --days-back 1
```

## 🔒 Güvenlik ve Etik Kullanım

### Rate Limiting
- Minimum 1 saniye delay kullanın
- Çok fazla paralel istek göndermeyin
- Headless mode kullanın
- Gereksiz yere site yüklemeyin

### Veri Kalitesi
- Duplicate kontrolü aktif
- Eksik veri validasyonu
- Hata durumunda güvenli çıkış
- Veritabanı transaction'ları

## 📞 Destek

Herhangi bir sorun yaşarsanız:
1. Log dosyalarını kontrol edin
2. `--test-mode` ile küçük test yapın
3. Delay değerlerini artırın
4. Veritabanı log kayıtlarını inceleyin

## 🎉 Sonuç

Bu sistem ile:
- ✅ Otomatik mevzuat güncellemeleri
- ✅ Hata toleranslı veri çekme
- ✅ Gerçek zamanlı istatistikler
- ✅ Esnek zamanlama seçenekleri
- ✅ Performans optimizasyonu

elde edebilirsiniz! 🚀