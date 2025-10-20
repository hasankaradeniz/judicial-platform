# ParamPOS Entegrasyon Kurulum Rehberi

## 🎯 Genel Bakış
Bu dokümanda Lexatech uygulamasının ParamPOS ile entegrasyonu ve kurulum adımları açıklanmaktadır.

## 🔧 Tespit Edilen Sunucu Bilgileri

### Test Ortamı
- **Sunucu IP:** `176.88.86.40`
- **Client Code:** `141957`
- **Client Username:** `TP10169107`
- **Client Password:** `298F748436F7CD64`
- **GUID:** `81F6955C-CA1B-4383-B67D-EF8E998CAC46`

## ⚠️ Mevcut Durum

### 403 Hatası - IP Whitelisting
ParamPOS SOAP API'sı 403 hatası veriyor. Bu sorun aşağıdaki nedenlerden kaynaklanmaktadır:

1. **IP Adresi Kayıtlı Değil:** Sunucu IP adresi (`176.88.86.40`) ParamPOS test ortamında kayıtlı değil
2. **Güvenlik Kontrolü:** ParamPOS IP tabanlı güvenlik kontrolü yapıyor

### Fallback Çözümü
Sistem otomatik olarak şu adımları uyguluyor:

1. **SOAP API Denemesi:** İlk olarak SOAP API'sı denenir
2. **403 Hatası Tespit:** IP whitelisting hatası tespit edilir
3. **Form-Based Fallback:** Otomatik olarak form tabanlı ödeme yöntemine geçer
4. **Demo Mode (Localhost):** Yerel ortamda demo ödeme sayfası gösterilir

## 🔑 Çözüm Adımları

### Test Ortamı İçin
ParamPOS test ortamında IP kaydı için:

1. **E-posta Gönder:** `destek@param.com.tr` adresine e-posta gönderin
2. **IP Bilgisi:** `176.88.86.40` IP adresinin test ortamında kayıt edilmesini isteyiniz
3. **Client Code:** `141957` numaralı hesap için kayıt

### Production Ortamı İçin
ParamPOS production ortamında:

1. **Panel Giriş:** ParamPOS merchant panel'ine giriş yapın
2. **Navigasyon:** ParamPOS > My Integration Information bölümüne gidin
3. **IP Kaydı:** Sunucu IP adresini (`176.88.86.40`) kaydedin

## 🧪 Test Kartları

### Finansbank Test Kartları
- **Visa:** `4022774022774026`
- **MasterCard:** `5456165456165454`
- **Son Kullanma:** `12/26`
- **CVV:** `000`
- **3D Secure Şifre:** `a`

### Diğer Bankalar
- **Ziraat Bankası Visa:** `4546711234567894`
- **İş Bankası MasterCard:** `5406675406675403`
- **Akbank Visa:** `4355084355084358`

## 📋 Teknik Detaylar

### SOAP API Endpoint
```
Test: https://testposws.param.com.tr/turkpos.ws/service_turkpos_test.asmx
Production: https://posws.param.com.tr/turkpos.ws/service_turkpos_prod.asmx
```

### Form-Based Payment URL
```
Test: https://test-pos-mp.param.com.tr/Payment.aspx
Production: https://pos-mp.param.com.tr/Payment.aspx
```

### Gerekli Parametreler
- `CLIENT_CODE`: Merchant kodu
- `CLIENT_USERNAME`: Kullanıcı adı
- `GUID`: Benzersiz tanımlayıcı
- `MERCHANT_OID`: Sipariş numarası
- `TOTAL_AMOUNT`: Tutar (kuruş cinsinden)
- `CURRENCY`: Para birimi (TL)
- `HASH`: Güvenlik hash'i (HMAC-SHA256)

## 🔄 Mevcut İmplementasyon

### Otomatik Fallback Sistemi
```python
# 1. SOAP API denemesi
if soap_api_call() == 403:
    # 2. Form-based fallback
    return create_form_payment()
elif localhost:
    # 3. Demo mode
    return create_demo_payment()
```

### Demo Mode (Localhost)
Yerel geliştirme ortamında:
- Demo ödeme sayfası gösterilir
- Başarılı/başarısız ödeme simülasyonu yapılabilir
- Gerçek ödeme işlemi yapılmaz

## ✅ Doğrulama Adımları

1. **IP Kaydı Sonrası:**
   - SOAP API test edin
   - 403 hatası gitmeli
   - Payment URL düzgün oluşmalı

2. **Form Payment Test:**
   - Test kartları ile ödeme deneyin
   - 3D Secure akışını test edin
   - Callback URL'leri kontrol edin

3. **Production Deployment:**
   - DNS ayarlarını kontrol edin
   - SSL sertifikasını doğrulayın
   - Webhook URL'leri test edin

## 🚨 Güvenlik Notları

- Client Password'u güvenli tutun
- HASH değerini her istekte hesaplayın
- Callback'leri doğrulayın
- Test kartlarını production'da kullanmayın

## 📞 Destek

ParamPOS ile ilgili sorunlar için:
- **E-posta:** `destek@param.com.tr`
- **Dokümantasyon:** https://dev.param.com.tr
- **GitHub Örnekleri:** https://github.com/PARAMPOS/API-Kullanim-Ornekleri

---

**Not:** Bu dokümandaki bilgiler 18 Temmuz 2025 tarihinde güncellenmiştir.