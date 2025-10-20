# ParamPOS IP Kayıt Talebi

## 📧 E-posta Bilgileri

**Gönderilecek Adres:** `destek@param.com.tr`

**Konu:** Test Ortamı IP Kaydı Talebi - Terminal: 141957

## 📝 E-posta İçeriği

```
Merhaba ParamPOS Destek Ekibi,

Lexatech uygulaması için ParamPOS test ortamında IP kaydı yapılmasını talep ediyoruz.

HESAP BİLGİLERİ:
- Terminal No (CLIENT_CODE): 141957
- Web Servis Kullanıcı Adı (CLIENT_USERNAME): TP10169107
- Web Servis Kullanıcı Şifre (CLIENT_PASSWORD): 298F748436F7CD64
- Anahtar (GUID): 81F6955C-CA1B-4383-B67D-EF8E998CAC46

SUNUCU BİLGİLERİ:
- Kayıt edilecek IP Adresi: 145.223.82.130
- Domain: lexatech.ai
- Sunucu Lokasyonu: Türkiye

TEKNIK DETAYLAR:
- Kullanılacak Endpoint: https://testposws.param.com.tr/turkpos.ws/service_turkpos_prod.asmx
- SOAP Method: TP_Modal_Payment
- Mevcut Durum: 403 Access Denied hatası alıyoruz

Test ortamında SOAP API erişimi için bu IP adresinin kayıt edilmesini rica ederiz.

Teşekkürler,
Lexatech Geliştirme Ekibi
info@lexatech.ai
```

## 🔄 Mevcut Durum

✅ **Kod Hazır:** SOAP API tam implementasyon tamamlandı  
✅ **Credentials:** Doğru credentials kullanılıyor  
✅ **Endpoint:** Doğru SOAP endpoint kullanılıyor  
❌ **IP Kaydı:** 145.223.82.130 adresi kayıtlı değil (403 hatası)  

## ⏱️ Beklenen Süreç

1. E-posta gönderimi
2. ParamPOS teknik ekip onayı (1-2 iş günü)
3. IP kaydı tamamlandığında sistem otomatik çalışacak

## 🧪 IP Kaydı Sonrası Test

IP kaydı tamamlandığında:
- SOAP API 200 OK dönecek
- Payment URL alınacak
- Kullanıcı ParamPOS ödeme sayfasına yönlendirilecek

## 🚨 Kritik Not

**Form-based payment endpoint'i (`https://test-pos-mp.param.com.tr/Payment.aspx`) kullanılamıyor çünkü bu endpoint artık mevcut değil veya deprecated. Bu nedenden sadece SOAP API kullanılmalı.**