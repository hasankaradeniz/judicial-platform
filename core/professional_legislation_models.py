# Profesyonel Mevzuat Sistemi - Yeni Modeller
# Bu dosya mevcut models.py'ye eklenecek

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.urls import reverse
import re

# ========================
# PROFESYONEL MEVZUAT SİSTEMİ
# ========================

class LegislationType(models.Model):
    """Mevzuat türleri (Kanun, Yönetmelik, Tebliğ vs.)"""
    
    name = models.CharField("Tür Adı", max_length=100, unique=True)
    code = models.CharField("Tür Kodu", max_length=20, unique=True)
    description = models.TextField("Açıklama", blank=True, null=True)
    
    # Hiyerarşi sıralaması
    hierarchy_level = models.IntegerField("Hiyerarşi Seviyesi", default=1,
                                         help_text="1=En üst (Anayasa), 2=Kanun, 3=KHK, 4=Yönetmelik, 5=Tebliğ")
    display_order = models.IntegerField("Gösterim Sırası", default=0)
    
    # Görsel ayarlar
    color_code = models.CharField("Renk Kodu", max_length=7, default="#007bff",
                                 help_text="Hex renk kodu (örn: #ff0000)")
    icon_class = models.CharField("İkon Sınıfı", max_length=50, blank=True, null=True,
                                 help_text="CSS ikon sınıfı (örn: fas fa-balance-scale)")
    
    is_active = models.BooleanField("Aktif", default=True)
    created_at = models.DateTimeField("Oluşturulma", auto_now_add=True)
    
    class Meta:
        verbose_name = "Mevzuat Türü"
        verbose_name_plural = "Mevzuat Türleri"
        ordering = ['hierarchy_level', 'display_order', 'name']
    
    def __str__(self):
        return self.name

class LegislationCategory(models.Model):
    """Mevzuat kategorileri (Hukuk alanlarına göre)"""
    
    name = models.CharField("Kategori Adı", max_length=150)
    code = models.CharField("Kategori Kodu", max_length=30, unique=True)
    description = models.TextField("Açıklama", blank=True, null=True)
    
    # Hiyerarşi
    parent_category = models.ForeignKey('self', on_delete=models.CASCADE, 
                                       blank=True, null=True, 
                                       verbose_name="Üst Kategori",
                                       related_name='subcategories')
    
    # SEO ve görsel
    slug = models.SlugField("URL Dostu Ad", max_length=200, unique=True)
    icon_class = models.CharField("İkon", max_length=50, blank=True, null=True)
    color_code = models.CharField("Renk", max_length=7, default="#28a745")
    
    # Durum
    is_active = models.BooleanField("Aktif", default=True)
    display_order = models.IntegerField("Sıra", default=0)
    
    class Meta:
        verbose_name = "Mevzuat Kategorisi"
        verbose_name_plural = "Mevzuat Kategorileri"
        ordering = ['display_order', 'name']
    
    def __str__(self):
        if self.parent_category:
            return f"{self.parent_category.name} > {self.name}"
        return self.name
    
    def get_full_path(self):
        """Tam kategori yolunu döndür"""
        if self.parent_category:
            return f"{self.parent_category.get_full_path()} > {self.name}"
        return self.name

class ProfessionalLegislation(models.Model):
    """Profesyonel mevzuat ana modeli"""
    
    # Temel bilgiler
    title = models.CharField("Başlık", max_length=800)
    short_title = models.CharField("Kısa Başlık", max_length=200, blank=True, null=True)
    legislation_type = models.ForeignKey(LegislationType, on_delete=models.PROTECT, 
                                        verbose_name="Mevzuat Türü")
    category = models.ForeignKey(LegislationCategory, on_delete=models.SET_NULL,
                                blank=True, null=True, verbose_name="Kategori")
    
    # Numaralandırma
    number = models.CharField("Mevzuat Numarası", max_length=100, blank=True, null=True)
    sequence = models.CharField("Sıra Numarası", max_length=50, blank=True, null=True)
    
    # Resmi Gazete bilgileri
    official_gazette_date = models.DateField("Resmi Gazete Tarihi", blank=True, null=True)
    official_gazette_number = models.CharField("Resmi Gazete Sayısı", max_length=20, blank=True, null=True)
    duplicate_number = models.CharField("Mükerrer Sayısı", max_length=10, blank=True, null=True)
    
    # Tarihler
    publication_date = models.DateField("Yayın Tarihi", blank=True, null=True)
    effective_date = models.DateField("Yürürlük Tarihi", blank=True, null=True)
    expiry_date = models.DateField("Yürürlük Bitiş Tarihi", blank=True, null=True)
    acceptance_date = models.DateField("Kabul Tarihi", blank=True, null=True)
    
    # İçerik
    subject = models.TextField("Konu", blank=True, null=True)
    summary = models.TextField("Özet", blank=True, null=True)
    keywords = models.TextField("Anahtar Kelimeler", blank=True, null=True,
                               help_text="Virgülle ayırınız")
    
    # Durum
    STATUS_CHOICES = [
        ('active', 'Yürürlükte'),
        ('repealed', 'Yürürlükten Kaldırıldı'),
        ('amended', 'Değiştirildi'),
        ('superseded', 'Yerine Başkası Geldi'),
        ('suspended', 'Askıya Alındı'),
        ('draft', 'Taslak'),
    ]
    status = models.CharField("Durum", max_length=20, choices=STATUS_CHOICES, default='active')
    
    # İlişkiler
    related_legislations = models.ManyToManyField('self', blank=True, symmetrical=False,
                                                 verbose_name="İlgili Mevzuatlar")
    superseded_by = models.ForeignKey('self', on_delete=models.SET_NULL, 
                                     blank=True, null=True,
                                     verbose_name="Yerine Geçen")
    
    # Kaynak bilgileri
    source_url = models.URLField("Kaynak URL", blank=True, null=True)
    mevzuat_gov_id = models.CharField("Mevzuat.gov.tr ID", max_length=100, 
                                     blank=True, null=True, unique=True)
    pdf_url = models.URLField("PDF URL", blank=True, null=True)
    
    # Metinler
    full_text = models.TextField("Tam Metin", blank=True, null=True)
    full_text_html = models.TextField("HTML Metin", blank=True, null=True)
    
    # SEO
    slug = models.SlugField("URL", max_length=300, unique=True, blank=True)
    meta_description = models.CharField("Meta Açıklama", max_length=300, blank=True, null=True)
    
    # İstatistikler
    view_count = models.PositiveIntegerField("Görüntülenme", default=0)
    search_count = models.PositiveIntegerField("Arama Sayısı", default=0)
    
    # Sistem alanları
    created_at = models.DateTimeField("Kayıt Tarihi", auto_now_add=True)
    updated_at = models.DateTimeField("Güncelleme Tarihi", auto_now=True)
    last_checked = models.DateTimeField("Son Kontrol", blank=True, null=True)
    
    # Veri kalitesi
    is_verified = models.BooleanField("Doğrulandı", default=False)
    verification_date = models.DateTimeField("Doğrulama Tarihi", blank=True, null=True)
    data_quality_score = models.FloatField("Veri Kalite Skoru", default=0.0,
                                          help_text="0-100 arası")
    
    class Meta:
        verbose_name = "Profesyonel Mevzuat"
        verbose_name_plural = "Profesyonel Mevzuatlar"
        ordering = ['-publication_date', '-created_at']
        indexes = [
            models.Index(fields=['legislation_type', 'status']),
            models.Index(fields=['publication_date']),
            models.Index(fields=['official_gazette_date']),
            models.Index(fields=['mevzuat_gov_id']),
            models.Index(fields=['slug']),
            models.Index(fields=['status']),
        ]
    
    def save(self, *args, **kwargs):
        # Slug oluştur
        if not self.slug:
            from django.utils.text import slugify
            base_slug = slugify(self.title[:250])
            slug = base_slug
            counter = 1
            while ProfessionalLegislation.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('legislation_detail', kwargs={'slug': self.slug})
    
    def __str__(self):
        if self.number:
            return f"{self.title} ({self.number})"
        return self.title
    
    def is_active(self):
        return self.status == 'active'
    
    def get_display_title(self):
        """Görüntüleme için optimize edilmiş başlık"""
        if self.short_title:
            return self.short_title
        return self.title[:200] + "..." if len(self.title) > 200 else self.title

class LegislationPart(models.Model):
    """Mevzuat kısım/bölüm yönetimi"""
    
    legislation = models.ForeignKey(ProfessionalLegislation, on_delete=models.CASCADE,
                                   related_name='parts', verbose_name="Mevzuat")
    
    # Hiyerarşi
    PART_TYPES = [
        ('part', 'Kısım'),
        ('section', 'Bölüm'),
        ('chapter', 'Bap'),
        ('title', 'Başlık'),
        ('subtitle', 'Alt Başlık'),
    ]
    
    part_type = models.CharField("Tür", max_length=20, choices=PART_TYPES)
    number = models.CharField("Numara", max_length=20, blank=True, null=True)
    title = models.CharField("Başlık", max_length=500)
    
    # Hiyerarşi
    parent_part = models.ForeignKey('self', on_delete=models.CASCADE, 
                                   blank=True, null=True,
                                   verbose_name="Üst Kısım")
    order = models.IntegerField("Sıra", default=0)
    
    # İçerik
    description = models.TextField("Açıklama", blank=True, null=True)
    
    # Durum
    is_active = models.BooleanField("Aktif", default=True)
    
    class Meta:
        verbose_name = "Mevzuat Kısmı"
        verbose_name_plural = "Mevzuat Kısımları"
        ordering = ['order', 'id']
        unique_together = ['legislation', 'part_type', 'number']
    
    def __str__(self):
        parts = []
        if self.number:
            parts.append(f"{self.get_part_type_display()} {self.number}")
        else:
            parts.append(self.get_part_type_display())
        parts.append(self.title)
        return " - ".join(parts)

class LegislationArticle(models.Model):
    """Mevzuat maddeleri"""
    
    legislation = models.ForeignKey(ProfessionalLegislation, on_delete=models.CASCADE,
                                   related_name='articles', verbose_name="Mevzuat")
    part = models.ForeignKey(LegislationPart, on_delete=models.CASCADE,
                            blank=True, null=True, related_name='articles',
                            verbose_name="Bağlı Kısım")
    
    # Madde bilgileri
    article_number = models.CharField("Madde Numarası", max_length=50)
    title = models.CharField("Madde Başlığı", max_length=500, blank=True, null=True)
    
    # İçerik
    text = models.TextField("Madde Metni")
    text_html = models.TextField("HTML Metin", blank=True, null=True)
    
    # Notlar
    footnotes = models.TextField("Dipnotlar", blank=True, null=True)
    legal_notes = models.TextField("Hukuki Notlar", blank=True, null=True)
    
    # Sıralama
    order = models.IntegerField("Sıra", default=0)
    
    # Durum
    is_active = models.BooleanField("Aktif", default=True)
    is_repealed = models.BooleanField("Yürürlükten Kaldırıldı", default=False)
    repeal_date = models.DateField("Kaldırılma Tarihi", blank=True, null=True)
    
    # İstatistik
    view_count = models.PositiveIntegerField("Görüntülenme", default=0)
    
    class Meta:
        verbose_name = "Madde"
        verbose_name_plural = "Maddeler"
        ordering = ['order', 'article_number']
        unique_together = ['legislation', 'article_number']
        indexes = [
            models.Index(fields=['legislation', 'is_active']),
            models.Index(fields=['article_number']),
        ]
    
    def __str__(self):
        parts = [f"Madde {self.article_number}"]
        if self.title:
            parts.append(f"({self.title[:50]}...)" if len(self.title) > 50 else f"({self.title})")
        return " ".join(parts)
    
    def get_display_text(self):
        """Görüntüleme için formatlanmış metin"""
        if self.text_html:
            return self.text_html
        return self.text.replace('\n', '<br>')
    
    def get_search_text(self):
        """Arama için düz metin"""
        return f"{self.title or ''} {self.text}"

class LegislationParagraph(models.Model):
    """Madde fıkraları"""
    
    article = models.ForeignKey(LegislationArticle, on_delete=models.CASCADE,
                               related_name='paragraphs', verbose_name="Madde")
    
    # Fıkra bilgileri
    paragraph_number = models.CharField("Fıkra Numarası", max_length=20, blank=True, null=True)
    text = models.TextField("Fıkra Metni")
    text_html = models.TextField("HTML Metin", blank=True, null=True)
    
    # Sıralama
    order = models.IntegerField("Sıra", default=0)
    
    # Durum
    is_active = models.BooleanField("Aktif", default=True)
    
    class Meta:
        verbose_name = "Fıkra"
        verbose_name_plural = "Fıkralar"
        ordering = ['order']
    
    def __str__(self):
        if self.paragraph_number:
            return f"({self.paragraph_number}) {self.text[:100]}..."
        return f"Fıkra: {self.text[:100]}..."

class LegislationSubitem(models.Model):
    """Madde bentleri"""
    
    paragraph = models.ForeignKey(LegislationParagraph, on_delete=models.CASCADE,
                                 related_name='subitems', verbose_name="Fıkra")
    
    # Bent bilgileri
    SUBITEM_TYPES = [
        ('letter', 'Harf (a, b, c)'),
        ('number', 'Sayı (1, 2, 3)'),
        ('roman', 'Roma (I, II, III)'),
    ]
    
    subitem_type = models.CharField("Bent Türü", max_length=10, choices=SUBITEM_TYPES, default='letter')
    subitem_number = models.CharField("Bent Numarası", max_length=10)
    text = models.TextField("Bent Metni")
    text_html = models.TextField("HTML Metin", blank=True, null=True)
    
    # Sıralama
    order = models.IntegerField("Sıra", default=0)
    
    # Durum
    is_active = models.BooleanField("Aktif", default=True)
    
    class Meta:
        verbose_name = "Bent"
        verbose_name_plural = "Bentler"
        ordering = ['order']
        unique_together = ['paragraph', 'subitem_number']
    
    def __str__(self):
        return f"{self.subitem_number}) {self.text[:100]}..."

class CourtDecisionLegislationRelation(models.Model):
    """Yargıtay kararları ile mevzuat arasındaki ilişki"""
    
    court_decision = models.ForeignKey('JudicialDecision', on_delete=models.CASCADE,
                                      verbose_name="Yargıtay Kararı")
    legislation = models.ForeignKey(ProfessionalLegislation, on_delete=models.CASCADE,
                                   verbose_name="Mevzuat")
    article = models.ForeignKey(LegislationArticle, on_delete=models.CASCADE,
                               blank=True, null=True, verbose_name="İlgili Madde")
    
    # İlişki türü
    RELATION_TYPES = [
        ('application', 'Uygulama'),
        ('interpretation', 'Yorum'),
        ('precedent', 'İçtihat'),
        ('contradiction', 'Çelişki'),
        ('reference', 'Atıf'),
    ]
    
    relation_type = models.CharField("İlişki Türü", max_length=20, choices=RELATION_TYPES)
    description = models.TextField("Açıklama", blank=True, null=True)
    
    # Güvenilirlik
    confidence_score = models.FloatField("Güven Skoru", default=0.0,
                                        help_text="0-1 arası otomatik tespit güveni")
    is_verified = models.BooleanField("Doğrulandı", default=False)
    
    # Sistem
    created_at = models.DateTimeField("Oluşturulma", auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, 
                                  blank=True, null=True,
                                  verbose_name="Oluşturan")
    
    class Meta:
        verbose_name = "Karar-Mevzuat İlişkisi"
        verbose_name_plural = "Karar-Mevzuat İlişkileri"
        unique_together = ['court_decision', 'legislation', 'article']
    
    def __str__(self):
        article_info = f" (Madde {self.article.article_number})" if self.article else ""
        return f"{self.court_decision} ↔ {self.legislation}{article_info}"

class LegislationAmendment(models.Model):
    """Mevzuat değişiklik takibi"""
    
    legislation = models.ForeignKey(ProfessionalLegislation, on_delete=models.CASCADE,
                                   related_name='amendments', verbose_name="Mevzuat")
    amending_legislation = models.ForeignKey(ProfessionalLegislation, on_delete=models.CASCADE,
                                           related_name='amendments_made',
                                           verbose_name="Değiştiren Mevzuat")
    
    # Değişiklik detayları
    AMENDMENT_TYPES = [
        ('addition', 'Madde Ekleme'),
        ('deletion', 'Madde Silme'),
        ('modification', 'Madde Değiştirme'),
        ('replacement', 'Madde Değiştirme'),
        ('repeal', 'Yürürlükten Kaldırma'),
    ]
    
    amendment_type = models.CharField("Değişiklik Türü", max_length=20, choices=AMENDMENT_TYPES)
    affected_articles = models.ManyToManyField(LegislationArticle, blank=True,
                                              verbose_name="Etkilenen Maddeler")
    description = models.TextField("Değişiklik Açıklaması")
    
    # Tarihler
    amendment_date = models.DateField("Değişiklik Tarihi")
    effective_date = models.DateField("Yürürlük Tarihi")
    
    # Sistem
    created_at = models.DateTimeField("Kayıt Tarihi", auto_now_add=True)
    
    class Meta:
        verbose_name = "Mevzuat Değişikliği"
        verbose_name_plural = "Mevzuat Değişiklikleri"
        ordering = ['-amendment_date']
    
    def __str__(self):
        return f"{self.legislation.title} - {self.get_amendment_type_display()} ({self.amendment_date})"

class LegislationSearchLog(models.Model):
    """Arama logları ve istatistikleri"""
    
    query = models.CharField("Arama Sorgusu", max_length=500)
    legislation = models.ForeignKey(ProfessionalLegislation, on_delete=models.CASCADE,
                                   blank=True, null=True, verbose_name="Bulunan Mevzuat")
    article = models.ForeignKey(LegislationArticle, on_delete=models.CASCADE,
                               blank=True, null=True, verbose_name="Bulunan Madde")
    
    # Kullanıcı bilgisi
    user = models.ForeignKey(User, on_delete=models.SET_NULL, 
                            blank=True, null=True, verbose_name="Kullanıcı")
    ip_address = models.GenericIPAddressField("IP Adresi", blank=True, null=True)
    user_agent = models.TextField("Tarayıcı Bilgisi", blank=True, null=True)
    
    # Arama detayları
    search_type = models.CharField("Arama Türü", max_length=50, 
                                  choices=[
                                      ('full_text', 'Tam Metin'),
                                      ('title', 'Başlık'),
                                      ('article', 'Madde'),
                                      ('number', 'Numara'),
                                  ])
    results_count = models.IntegerField("Sonuç Sayısı", default=0)
    response_time = models.FloatField("Yanıt Süresi (ms)", default=0.0)
    
    # Sistem
    created_at = models.DateTimeField("Arama Zamanı", auto_now_add=True)
    
    class Meta:
        verbose_name = "Arama Logu"
        verbose_name_plural = "Arama Logları"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['query', 'created_at']),
            models.Index(fields=['user', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.query} ({self.created_at})"