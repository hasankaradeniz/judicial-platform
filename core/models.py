# core/models.py
from django.db import models
import io
import mammoth
import fitz
import re
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from django.core.validators import MinLengthValidator, RegexValidator
from django.utils.timezone import now
from django.db.models.signals import post_save
from django.dispatch import receiver

class UserProfile(models.Model):
    """Kullanıcı profil bilgileri için ek model"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone_number = models.CharField(
        "Telefon Numarası", 
        max_length=15,
        validators=[
            RegexValidator(
                r'^[\+\d\s\-\(\)]+$', 
                "Geçerli bir telefon numarası giriniz. (Örn: 05551234567 veya +90 555 123 45 67)"
            )
        ],
        help_text="Telefon numaranızı giriniz"
    )
    
    # Adres bilgileri - fatura için gerekli
    address_line_1 = models.CharField(
        "Adres Satırı 1", 
        max_length=255,
        blank=True,
        null=True,
        help_text="Mahalle, cadde, sokak ve kapı numarası"
    )
    address_line_2 = models.CharField(
        "Adres Satırı 2", 
        max_length=255,
        blank=True,
        null=True,
        help_text="Apartman, daire numarası gibi ek adres bilgileri (opsiyonel)"
    )
    city = models.CharField(
        "Şehir", 
        max_length=100,
        blank=True,
        null=True
    )
    district = models.CharField(
        "İlçe", 
        max_length=100,
        blank=True,
        null=True
    )
    postal_code = models.CharField(
        "Posta Kodu", 
        max_length=10,
        blank=True,
        null=True,
        validators=[
            RegexValidator(
                r'^\d{5}$', 
                "Geçerli bir posta kodu giriniz. (Örn: 34000)"
            )
        ]
    )
    
    is_free_trial = models.BooleanField("Ücretsiz Deneme", default=True)
    free_trial_start = models.DateTimeField("Ücretsiz Deneme Başlangıç", auto_now_add=True)
    free_trial_end = models.DateTimeField("Ücretsiz Deneme Bitiş", null=True, blank=True)
    created_at = models.DateTimeField("Oluşturulma Tarihi", auto_now_add=True)
    updated_at = models.DateTimeField("Güncellenme Tarihi", auto_now=True)
    
    class Meta:
        verbose_name = "Kullanıcı Profili"
        verbose_name_plural = "Kullanıcı Profilleri"
    
    def save(self, *args, **kwargs):
        # Ücretsiz deneme bitiş tarihini otomatik hesapla (2 ay = 60 gün)
        if not self.free_trial_end and self.is_free_trial:
            if not self.free_trial_start:
                self.free_trial_start = timezone.now()
            self.free_trial_end = self.free_trial_start + timedelta(days=30)
        super().save(*args, **kwargs)
    
    def is_free_trial_expired(self):
        """Ücretsiz deneme süresi dolmuş mu kontrol et"""
        if not self.is_free_trial:
            return False
        return timezone.now() > self.free_trial_end if self.free_trial_end else False
    
    def has_active_subscription(self):
        """Aktif aboneliği var mı kontrol et"""
        try:
            subscription = self.user.subscription
            return subscription.end_date > timezone.now()
        except Subscription.DoesNotExist:
            return False
    
    def can_access_platform(self):
        """Platform erişimi var mı kontrol et"""
        return (self.is_free_trial and not self.is_free_trial_expired()) or self.has_active_subscription()
    
    def get_remaining_trial_days(self):
        """Kalan deneme gün sayısını döndür"""
        if not self.is_free_trial or not self.free_trial_end:
            return 0
        remaining = (self.free_trial_end - timezone.now()).days
        return max(0, remaining)
    
    def is_trial_ending_soon(self):
        """Deneme süresi 7 gün içinde bitiyor mu"""
        return self.is_free_trial and self.get_remaining_trial_days() <= 7
    
    def __str__(self):
        return f"{self.user.username} - {self.phone_number}"

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Yeni kullanıcı oluşturulduğunda otomatik profil oluştur"""
    if created:
        try:
            profile = UserProfile.objects.create(user=instance)
            # Ensure free trial dates are set (2 ay = 60 gün)
            if not profile.free_trial_start:
                profile.free_trial_start = timezone.now()
            if not profile.free_trial_end:
                profile.free_trial_end = profile.free_trial_start + timedelta(days=30)
            profile.save()
        except Exception as e:
            print(f"Error creating user profile: {e}")

# Bu signal probleme neden oluyor - geçici olarak devre dışı
# @receiver(post_save, sender=User)
# def save_user_profile(sender, instance, **kwargs):
#     """Kullanıcı kaydedildiğinde profili de kaydet"""
#     with open('/tmp/signup_debug.log', 'a') as f:
#         f.write(f"=== POST_SAVE SIGNAL ÇALIŞTI === User: {instance.username}\n")
#     try:
#         if hasattr(instance, 'profile'):
#             with open('/tmp/signup_debug.log', 'a') as f:
#                 f.write(f"Profile mevcut, kaydediliyor...\n")
#             instance.profile.save()
#             with open('/tmp/signup_debug.log', 'a') as f:
#                 f.write(f"Profile kaydedildi.\n")
#     except Exception as e:
#         with open('/tmp/signup_debug.log', 'a') as f:
#             f.write(f"Error saving user profile: {e}\n")

class JudicialDecision(models.Model):
    karar_turu = models.CharField("Karar Türü", max_length=255)
    karar_veren_mahkeme = models.CharField("Kararı Veren Mahkeme", max_length=255)
    esas_numarasi = models.CharField("Esas Numarası", max_length=100, blank=True, null=True)
    karar_numarasi = models.CharField("Karar Numarası", max_length=100, blank=True, null=True)
    karar_tarihi = models.DateField("Karar Tarihi", blank=True, null=True)
    anahtar_kelimeler = models.TextField("Anahtar Kelimeler", blank=True, null=True)
    detected_legal_area = models.CharField("Tespit Edilen Hukuk Alanı", max_length=50, blank=True, null=True, 
                                         help_text="Otomatik tespit edilen hukuk alanı")
    
    def save(self, *args, **kwargs):
        # Anahtar kelime otomatik üretimi
        if not self.anahtar_kelimeler and self.karar_ozeti:
            self.anahtar_kelimeler = self.generate_keywords()
        super().save(*args, **kwargs)
    
    def generate_keywords(self):
        """Karar özetinden otomatik anahtar kelime üretimi"""
        if not self.karar_ozeti:
            return ""
        
        # Basit anahtar kelime çıkarımı
        import re
        text = self.karar_ozeti.lower()
        
        # Hukuki terimler sözlüğü
        legal_terms = {
            'miras': ['miras', 'tereke', 'vasiyet', 'muris'],
            'sözleşme': ['sözleşme', 'anlaşma', 'mukavele'],
            'tazminat': ['tazminat', 'zarar', 'maddi zarar'],
            'borç': ['borç', 'yükümlülük', 'ifa'],
            'aile': ['boşanma', 'nafaka', 'velayet'],
            'kira': ['kira', 'kiracı', 'kiraya'],
            'iş': ['işçi', 'işveren', 'iş sözleşmesi'],
            'mülkiyet': ['mülkiyet', 'tapu', 'gayrimenkul'],
            'dava': ['dava', 'davacı', 'davalı'],
            'iptal': ['iptal', 'fesih', 'geçersiz']
        }
        
        found_keywords = []
        
        # Hukuki terimler kontrolü
        for main_term, variants in legal_terms.items():
            for variant in variants:
                if variant in text:
                    found_keywords.append(main_term)
                    break
        
        # Karar türüne göre ek kelimeler
        if self.karar_turu:
            karar_turu_lower = self.karar_turu.lower()
            if 'miras' in karar_turu_lower:
                found_keywords.extend(['miras hukuku', 'tenkis', 'saklı pay'])
            elif 'borç' in karar_turu_lower:
                found_keywords.extend(['borçlar hukuku', 'sözleşme'])
            elif 'aile' in karar_turu_lower:
                found_keywords.extend(['aile hukuku', 'evlilik'])
        
        # Mahkeme türüne göre ek kelimeler
        if self.karar_veren_mahkeme:
            mahkeme_lower = self.karar_veren_mahkeme.lower()
            if 'yargıtay' in mahkeme_lower:
                found_keywords.append('yargıtay kararı')
            elif 'danıştay' in mahkeme_lower:
                found_keywords.append('idari yargı')
        
        # Sayıları ve miktarları bul
        amounts = re.findall(r'\d+\.?\d*\s*(?:tl|lira)', text)
        if amounts:
            found_keywords.append('maddi tazminat')
        
        # Tarihleri bul
        dates = re.findall(r'\d{1,2}[./]\d{1,2}[./]\d{4}', text)
        if dates:
            found_keywords.append('tarihli karar')
        
        # Benzersiz anahtar kelimeleri döndür
        unique_keywords = list(set(found_keywords))
        return ', '.join(unique_keywords[:10])
    karar_ozeti = models.TextField("Kararın Özeti", blank=True, null=True)
    karar_tam_metni = models.TextField("Kararın Tam Metni", blank=True, null=True)
    dosya = models.FileField("Dosya", upload_to='decisions/', blank=True, null=True)

    # Property methods for compatibility with new system
    @property
    def title(self):
        """Compatibility property for title"""
        return f"{self.karar_turu} - {self.karar_numarasi or ''}"
    
    @property
    def summary(self):
        """Compatibility property for summary"""
        return self.karar_ozeti
    
    @property
    def full_text(self):
        """Compatibility property for full text"""
        return self.karar_tam_metni
    
    @property
    def decision_date(self):
        """Compatibility property for decision date"""
        return self.karar_tarihi
    
    @property
    def court_name(self):
        """Compatibility property for court name"""
        return self.karar_veren_mahkeme

    def __str__(self):
        return f"{self.karar_veren_mahkeme} - {self.karar_numarasi}"

class Article(models.Model):
    makale_basligi = models.CharField("Makale Başlığı", max_length=255, blank=True, null=True)
    dergi = models.CharField("Yayınlandığı Dergi", max_length=255, blank=True, null=True)
    yazarlar = models.CharField("Yazarlar", max_length=255, blank=True, null=True)
    makale_ozeti = models.TextField("Makale Özeti", blank=True, null=True)
    makale_metni = models.TextField("Makale Metni", blank=True, null=True)
    dosya = models.FileField("Dosya", upload_to='articles/', blank=True, null=True)

    def save(self, *args, **kwargs):
        # Eğer dosya yüklendiyse ve makale_metni henüz boşsa, dosyayı işleyip alanları dolduruyoruz.
        if self.dosya and not self.makale_metni:
            filename = self.dosya.name.lower()
            self.dosya.open('rb')
            file_content = self.dosya.read()
            self.dosya.seek(0)
            full_text = ""
            # DOCX dosyası için Mammoth kullanımı
            if filename.endswith('.docx'):
                file_io = io.BytesIO(file_content)
                result = mammoth.extract_raw_text(file_io)
                full_text = result.value
            # PDF dosyası için PyMuPDF kullanımı
            elif filename.endswith('.pdf'):
                try:
                    # PyMuPDF ile PDF içeriğini oku
                    doc = fitz.open(stream=file_content, filetype="pdf")
                    text_list = []
                    for page in doc:
                        text_list.append(page.get_text())
                    full_text = "\n".join(text_list)
                except Exception as e:
                    full_text = ""
            # Çıkan metni makale_metni alanına atıyoruz
            self.makale_metni = full_text

            # Aşağıdaki regex örnekleri, dosyanın içinde "Başlık:", "Dergi:", "Yazarlar:" ve "Özet:" gibi ifadeler bulunduğunu varsayar.
            # Bu ifadeler dosya içeriğine göre uyarlanmalıdır.
            title_match = re.search(r"Başlık\s*[:\-]\s*(.+)", full_text, re.IGNORECASE)
            if title_match:
                self.makale_basligi = title_match.group(1).strip()

            dergi_match = re.search(r"Dergi\s*[:\-]\s*(.+)", full_text, re.IGNORECASE)
            if dergi_match:
                self.dergi = dergi_match.group(1).strip()

            yazar_match = re.search(r"Yazarlar\s*[:\-]\s*(.+)", full_text, re.IGNORECASE)
            if yazar_match:
                self.yazarlar = yazar_match.group(1).strip()

            ozet_match = re.search(r"Özet\s*[:\-]\s*(.+)", full_text, re.IGNORECASE | re.DOTALL)
            if ozet_match:
                self.makale_ozeti = ozet_match.group(1).strip()

        super().save(*args, **kwargs)

    def __str__(self):
        return self.makale_basligi or "Makale"


class Legislation(models.Model):
    MEVZUAT_TURLERI = [
        ('kanun', 'Kanun'),
        ('tuzuk', 'Tüzük'),
        ('yonetmelik', 'Yönetmelik'),
        ('genelge', 'Genelge'),
        ('teblig', 'Tebliğ'),
        # Diğer türler...
    ]
    mevzuat_turu = models.CharField("Mevzuat Türü", max_length=50, choices=MEVZUAT_TURLERI)
    baslik = models.CharField("Başlık", max_length=255)
    mevzuat_numarasi = models.CharField("Mevzuat Numarası", max_length=100, blank=True, null=True)
    yayin_tarihi = models.DateField("Yayın Tarihi", blank=True, null=True)
    yurutulme_tarihi = models.DateField("Yürürlük Tarihi", blank=True, null=True)
    resmigazete_tarihi = models.DateField("Resmi Gazete Tarihi", blank=True, null=True)
    konu = models.CharField("Konu", max_length=255, blank=True, null=True)
    ozet = models.TextField("Özet", blank=True, null=True)
    tam_metin = models.TextField("Tam Metin", blank=True, null=True)
    dosya = models.FileField("Dosya", upload_to='legislation/', blank=True, null=True)
    tam_metin_html = models.TextField("Tam Metin (HTML)", blank=True, null=True)

    def save(self, *args, **kwargs):
        # Dönüştürme işlemi yalnızca dosya yeni yüklendiyse ve tam_metin_html boşsa yapılır.
        if self.dosya and not self.tam_metin_html:
            filename = self.dosya.name.lower()
            # DOCX dosyaları için Mammoth kullanımı:
            if filename.endswith('.docx'):
                self.dosya.open('rb')
                file_content = self.dosya.read()
                file_io = io.BytesIO(file_content)
                result = mammoth.convert_to_html(file_io)
                self.tam_metin_html = result.value
                self.dosya.seek(0)
            # PDF dosyaları için PyMuPDF kullanımı:
            elif filename.endswith('.pdf'):
                self.dosya.open('rb')
                file_content = self.dosya.read()
                try:
                    # BytesIO'dan direkt dosya içeriğini kullanarak açıyoruz.
                    doc = fitz.open(stream=file_content, filetype="pdf")
                    html_pages = []
                    for page in doc:
                        # Yeni API: get_text("html") kullanıyoruz.
                        page_html = page.get_text("html")
                        html_pages.append(page_html)
                    self.tam_metin_html = "\n".join(html_pages)
                except Exception as e:
                    # Hata durumunda istisna mesajını loglayabilir, burada basitçe mesaj gösteriyoruz.
                    self.tam_metin_html = "<p>PDF içeriği dönüştürülemedi: {}</p>".format(e)
                finally:
                    self.dosya.seek(0)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.baslik

# ========================
# GENİŞLETİLMİŞ MEVZUAT SİSTEMİ
# ========================

class MevzuatTuru(models.Model):
    """Gelişmiş mevzuat türü yönetimi"""
    KATEGORI_CHOICES = [
        ('kanun', 'Kanunlar'),
        ('cumhurbaskanligi_kararnamesi', 'Cumhurbaşkanlığı Kararnameleri'),
        ('bakanlar_kurulu_karari', 'Bakanlar Kurulu Kararları'),
        ('cumhurbaskani_karari', 'Cumhurbaşkanı Kararları'),
        ('yonetmelik', 'Yönetmelikler'),
        ('tuzuk', 'Tüzükler'),
        ('teblig', 'Tebliğler'),
        ('genelge', 'Genelgeler'),
        ('mülga', 'Mülga Mevzuat'),
        ('uluslararasi_andlasma', 'Uluslararası Andlaşmalar'),
    ]
    
    kod = models.CharField("Tür Kodu", max_length=50, unique=True)
    ad = models.CharField("Tür Adı", max_length=100)
    kategori = models.CharField("Kategori", max_length=50, choices=KATEGORI_CHOICES)
    aciklama = models.TextField("Açıklama", blank=True, null=True)
    aktif = models.BooleanField("Aktif", default=True)
    sira = models.IntegerField("Sıra", default=0)
    
    class Meta:
        verbose_name = "Mevzuat Türü"
        verbose_name_plural = "Mevzuat Türleri"
        ordering = ['sira', 'ad']
    
    def __str__(self):
        return self.ad

class MevzuatKategori(models.Model):
    """Mevzuat konularına göre kategoriler"""
    ad = models.CharField("Kategori Adı", max_length=100)
    kod = models.CharField("Kategori Kodu", max_length=20, unique=True)
    aciklama = models.TextField("Açıklama", blank=True, null=True)
    ust_kategori = models.ForeignKey('self', on_delete=models.CASCADE, 
                                    blank=True, null=True, 
                                    verbose_name="Üst Kategori")
    aktif = models.BooleanField("Aktif", default=True)
    
    class Meta:
        verbose_name = "Mevzuat Kategorisi"
        verbose_name_plural = "Mevzuat Kategorileri"
        ordering = ['ad']
    
    def __str__(self):
        return self.ad

class MevzuatGelismis(models.Model):
    """Geliştirilmiş mevzuat modeli"""
    
    # Temel Bilgiler
    baslik = models.CharField("Başlık", max_length=500)
    mevzuat_turu = models.ForeignKey(MevzuatTuru, on_delete=models.PROTECT, 
                                    verbose_name="Mevzuat Türü")
    kategori = models.ForeignKey(MevzuatKategori, on_delete=models.SET_NULL, 
                                blank=True, null=True, verbose_name="Kategori")
    
    # Numaralandırma
    mevzuat_numarasi = models.CharField("Mevzuat Numarası", max_length=100, 
                                       blank=True, null=True)
    sira_numarasi = models.CharField("Sıra Numarası", max_length=50, 
                                    blank=True, null=True)
    
    # Tarihler
    yayin_tarihi = models.DateField("Yayın Tarihi", blank=True, null=True)
    yurutulme_tarihi = models.DateField("Yürürlük Tarihi", blank=True, null=True)
    yurutulme_bitis_tarihi = models.DateField("Yürürlük Bitiş Tarihi", 
                                             blank=True, null=True)
    
    # Resmi Gazete Bilgileri
    resmi_gazete_tarihi = models.DateField("Resmi Gazete Tarihi", 
                                          blank=True, null=True)
    resmi_gazete_sayisi = models.CharField("Resmi Gazete Sayısı", max_length=20, 
                                          blank=True, null=True)
    mukerrer_sayisi = models.CharField("Mükerrer Sayısı", max_length=10, 
                                      blank=True, null=True)
    
    # İçerik
    konu = models.TextField("Konu", blank=True, null=True)
    ozet = models.TextField("Özet", blank=True, null=True)
    anahtar_kelimeler = models.TextField("Anahtar Kelimeler", blank=True, null=True)
    
    # Metinler
    tam_metin = models.TextField("Tam Metin", blank=True, null=True)
    tam_metin_html = models.TextField("Tam Metin (HTML)", blank=True, null=True)
    
    # İlişkiler
    ilgili_mevzuatlar = models.ManyToManyField('self', blank=True, 
                                              verbose_name="İlgili Mevzuatlar")
    
    # Durum Bilgileri
    DURUM_CHOICES = [
        ('yurutulme', 'Yürürlükte'),
        ('ilga', 'İlga Edildi'),
        ('degisiklik', 'Değişiklik Yapıldı'),
        ('mulga', 'Mülga'),
        ('geçici', 'Geçici'),
    ]
    durum = models.CharField("Durum", max_length=20, choices=DURUM_CHOICES, 
                            default='yurutulme')
    
    # Dosyalar
    dosya = models.FileField("Dosya", upload_to='mevzuat_gelismis/', 
                            blank=True, null=True)
    
    # Sistem Alanları
    kayit_tarihi = models.DateTimeField("Kayıt Tarihi", auto_now_add=True)
    guncelleme_tarihi = models.DateTimeField("Güncelleme Tarihi", auto_now=True)
    son_kontrol_tarihi = models.DateTimeField("Son Kontrol Tarihi", 
                                             blank=True, null=True)
    
    # Kaynak bilgisi
    kaynak_url = models.URLField("Kaynak URL", blank=True, null=True)
    mevzuat_gov_tr_id = models.CharField("Mevzuat.gov.tr ID", max_length=50, 
                                        blank=True, null=True, unique=True)
    
    class Meta:
        verbose_name = "Gelişmiş Mevzuat"
        verbose_name_plural = "Gelişmiş Mevzuatlar"
        ordering = ['-yayin_tarihi', '-id']
        indexes = [
            models.Index(fields=['mevzuat_turu', 'durum']),
            models.Index(fields=['yayin_tarihi']),
            models.Index(fields=['resmi_gazete_tarihi']),
            models.Index(fields=['mevzuat_gov_tr_id']),
        ]
    
    def __str__(self):
        return f"{self.baslik} ({self.mevzuat_numarasi or 'No: Yok'})"

class MevzuatMadde(models.Model):
    """Mevzuat maddelerini yönetim"""
    mevzuat = models.ForeignKey(MevzuatGelismis, on_delete=models.CASCADE, 
                               related_name='maddeler', verbose_name="Mevzuat")
    
    # Madde Bilgileri
    madde_no = models.CharField("Madde No", max_length=20)
    madde_basligi = models.CharField("Madde Başlığı", max_length=200, 
                                    blank=True, null=True)
    
    # Hiyerarşi
    ust_madde = models.ForeignKey('self', on_delete=models.CASCADE, 
                                 blank=True, null=True, 
                                 verbose_name="Üst Madde")
    bent_no = models.CharField("Bent No", max_length=10, blank=True, null=True)
    fıkra_no = models.CharField("Fıkra No", max_length=10, blank=True, null=True)
    
    # İçerik
    metin = models.TextField("Madde Metni")
    metin_html = models.TextField("Madde Metni (HTML)", blank=True, null=True)
    
    # Durum
    aktif = models.BooleanField("Aktif", default=True)
    sira = models.IntegerField("Sıra", default=0)
    
    # Sistem
    kayit_tarihi = models.DateTimeField("Kayıt Tarihi", auto_now_add=True)
    guncelleme_tarihi = models.DateTimeField("Güncelleme Tarihi", auto_now=True)
    
    class Meta:
        verbose_name = "Mevzuat Maddesi"
        verbose_name_plural = "Mevzuat Maddeleri"
        ordering = ['sira', 'madde_no']
        unique_together = ['mevzuat', 'madde_no', 'bent_no', 'fıkra_no']
    
    def __str__(self):
        parts = [f"Madde {self.madde_no}"]
        if self.bent_no:
            parts.append(f"Bent {self.bent_no}")
        if self.fıkra_no:
            parts.append(f"Fıkra {self.fıkra_no}")
        return " - ".join(parts)

class MevzuatDegisiklik(models.Model):
    """Mevzuat değişiklik geçmişi"""
    mevzuat = models.ForeignKey(MevzuatGelismis, on_delete=models.CASCADE, 
                               related_name='degisiklikler', 
                               verbose_name="Mevzuat")
    
    # Değişiklik Bilgileri
    DEGISIKLIK_TURU = [
        ('ekleme', 'Madde Ekleme'),
        ('silme', 'Madde Silme'),
        ('degistirme', 'Madde Değiştirme'),
        ('yeniden_duzenleme', 'Yeniden Düzenleme'),
        ('ilga', 'İlga'),
    ]
    
    degisiklik_turu = models.CharField("Değişiklik Türü", max_length=20, 
                                      choices=DEGISIKLIK_TURU)
    aciklama = models.TextField("Açıklama")
    
    # Değiştiren Mevzuat
    degistiren_mevzuat = models.ForeignKey(MevzuatGelismis, 
                                          on_delete=models.CASCADE, 
                                          related_name='degistirdikleri',
                                          verbose_name="Değiştiren Mevzuat")
    
    # Etkilenen Maddeler
    etkilenen_maddeler = models.ManyToManyField(MevzuatMadde, blank=True,
                                               verbose_name="Etkilenen Maddeler")
    
    # Tarihler
    degisiklik_tarihi = models.DateField("Değişiklik Tarihi")
    yurutulme_tarihi = models.DateField("Yürürlük Tarihi")
    
    # Sistem
    kayit_tarihi = models.DateTimeField("Kayıt Tarihi", auto_now_add=True)
    
    class Meta:
        verbose_name = "Mevzuat Değişikliği"
        verbose_name_plural = "Mevzuat Değişiklikleri"
        ordering = ['-degisiklik_tarihi']
    
    def __str__(self):
        return f"{self.mevzuat.baslik} - {self.get_degisiklik_turu_display()}"

class MevzuatLog(models.Model):
    """Sistem log kayıtları"""
    ISLEM_TURU = [
        ('ekleme', 'Ekleme'),
        ('guncelleme', 'Güncelleme'),
        ('silme', 'Silme'),
        ('scraping', 'Veri Çekme'),
        ('hata', 'Hata'),
    ]
    
    islem_turu = models.CharField("İşlem Türü", max_length=20, choices=ISLEM_TURU)
    aciklama = models.TextField("Açıklama")
    mevzuat = models.ForeignKey(MevzuatGelismis, on_delete=models.SET_NULL, 
                               blank=True, null=True, verbose_name="İlgili Mevzuat")
    kullanici = models.ForeignKey(User, on_delete=models.SET_NULL, 
                                 blank=True, null=True, verbose_name="Kullanıcı")
    ip_adresi = models.GenericIPAddressField("IP Adresi", blank=True, null=True)
    detaylar = models.JSONField("Detaylar", blank=True, null=True)
    
    # Sistem
    kayit_tarihi = models.DateTimeField("Kayıt Tarihi", auto_now_add=True)
    
    class Meta:
        verbose_name = "Mevzuat Log"
        verbose_name_plural = "Mevzuat Logları"
        ordering = ['-kayit_tarihi']
    
    def __str__(self):
        return f"{self.get_islem_turu_display()} - {self.kayit_tarihi}"

class Subscription(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    plan = models.CharField(max_length=20, choices=[
        ('monthly', 'Aylık'),
        ('quarterly', '3 Aylık'),
        ('semi_annually', '6 Aylık'),
        ('yearly', 'Yıllık')
    ])
    start_date = models.DateTimeField(default=now)
    end_date = models.DateTimeField(null=True, blank=True)

    # Yeni eklenen alanlar (null=True ve blank=True eklendi)
    tc_or_vergi_no = models.CharField(
        max_length=11,
        validators=[
            MinLengthValidator(10, "T.C. Kimlik veya Vergi Numarası en az 10 karakter olmalıdır."),
            RegexValidator(r'^\d+$', "Sadece rakam giriniz.")
        ],
        verbose_name="T.C. Kimlik / Vergi Numarası",
        null=True, blank=True  # Mevcut veriler için hata almamak adına eklendi
    )
    address = models.TextField(verbose_name="Adres", null=True, blank=True)  # Güncellendi

    # Kullanıcının satın alırken kabul ettiği sözleşmeler
    accepted_terms = models.BooleanField(default=False, verbose_name="Kullanıcı Sözleşmesi")
    accepted_sale = models.BooleanField(default=False, verbose_name="Mesafeli Satış Sözleşmesi")
    accepted_delivery = models.BooleanField(default=False, verbose_name="Teslimat & İade Şartları")


    def save(self, *args, **kwargs):
        # Eğer end_date henüz belirlenmemişse, plan tipine göre hesaplanır.
        if not self.end_date:
            if self.plan == 'monthly':
                self.end_date = self.start_date + timedelta(days=30)
            elif self.plan == 'quarterly':
                self.end_date = self.start_date + timedelta(days=90)
            elif self.plan == 'half_yearly':
                self.end_date = self.start_date + timedelta(days=180)
            elif self.plan == 'yearly':
                self.end_date = self.start_date + timedelta(days=365)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} - {self.get_plan_display()}"


class Payment(models.Model):
    """Ödeme işlemleri için model"""
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Beklemede'),
        ('success', 'Başarılı'),
        ('failed', 'Başarısız'),
        ('cancelled', 'İptal Edildi'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Kullanıcı")
    package = models.CharField(max_length=20, verbose_name="Paket")
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Tutar")
    currency = models.CharField(max_length=3, default='TRY', verbose_name="Para Birimi")
    order_id = models.CharField(max_length=100, unique=True, verbose_name="Sipariş No")
    transaction_id = models.CharField(max_length=100, blank=True, null=True, verbose_name="İşlem No")
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending', verbose_name="Durum")
    payment_method = models.CharField(max_length=50, default='param_pos', verbose_name="Ödeme Yöntemi")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturulma Tarihi")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Güncellenme Tarihi")
    error_message = models.TextField(blank=True, null=True, verbose_name="Hata Mesajı")
    
    # Param Pos spesifik alanlar
    param_hash = models.CharField(max_length=200, blank=True, null=True, verbose_name="Param Hash")
    param_response = models.JSONField(blank=True, null=True, verbose_name="Param Yanıtı")
    
    class Meta:
        verbose_name = "Ödeme"
        verbose_name_plural = "Ödemeler"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.order_id} - {self.get_status_display()}"

class Notification(models.Model):
    """Bildirim sistemi"""
    NOTIFICATION_TYPES = [
        ('purchase', 'Paket Satın Alma'),
        ('expiry_warning', 'Süre Dolma Uyarısı'),
        ('expiry', 'Süre Doldu'),
        ('free_trial_warning', 'Ücretsiz Deneme Bitiyor'),
        ('free_trial_expired', 'Ücretsiz Deneme Bitti'),
        ('system', 'Sistem Bildirimi'),
    ]
    
    notification_type = models.CharField("Bildirim Türü", max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField("Başlık", max_length=200)
    message = models.TextField("Mesaj")
    
    # İlgili kullanıcı (boşsa admin bildirimi)
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True, verbose_name="Kullanıcı")
    
    # İlgili payment/subscription
    payment = models.ForeignKey(Payment, on_delete=models.SET_NULL, blank=True, null=True, verbose_name="İlgili Ödeme")
    subscription = models.ForeignKey(Subscription, on_delete=models.SET_NULL, blank=True, null=True, verbose_name="İlgili Abonelik")
    
    # Bildirim durumu
    is_read = models.BooleanField("Okundu", default=False)
    is_sent_email = models.BooleanField("E-posta Gönderildi", default=False)
    is_admin_notification = models.BooleanField("Admin Bildirimi", default=False)
    
    # Tarihler
    created_at = models.DateTimeField("Oluşturulma Tarihi", auto_now_add=True)
    sent_at = models.DateTimeField("Gönderilme Tarihi", blank=True, null=True)
    read_at = models.DateTimeField("Okunma Tarihi", blank=True, null=True)
    
    # Extra data
    extra_data = models.JSONField("Ek Veriler", blank=True, null=True)
    
    class Meta:
        verbose_name = "Bildirim"
        verbose_name_plural = "Bildirimler"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['notification_type']),
            models.Index(fields=['is_admin_notification']),
        ]
    
    def mark_as_read(self):
        """Bildirimi okundu olarak işaretle"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()
    
    def send_email_notification(self):
        """E-posta bildirimi gönder"""
        if not self.is_sent_email and self.user and self.user.email:
            from django.core.mail import send_mail
            from django.conf import settings
            
            try:
                send_mail(
                    subject=f"Lexatech - {self.title}",
                    message=self.message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[self.user.email],
                    fail_silently=False,
                )
                self.is_sent_email = True
                self.sent_at = timezone.now()
                self.save()
                return True
            except Exception as e:
                print(f"E-posta gönderme hatası: {str(e)}")
                return False
        return False
    
    def __str__(self):
        user_info = f"{self.user.username}" if self.user else "Admin"
        return f"{user_info} - {self.title}"