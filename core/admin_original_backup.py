# core/admin.py
from django.contrib import admin
from .models import (
    JudicialDecision, Article, Legislation,
    MevzuatTuru, MevzuatKategori, MevzuatGelismis, 
    MevzuatMadde, MevzuatDegisiklik, MevzuatLog,
    Subscription, Payment
)

# Mevcut modeller
admin.site.register(JudicialDecision)
admin.site.register(Article)
admin.site.register(Legislation)

# Subscription ve Payment modelleri
@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'plan', 'start_date', 'end_date', 'accepted_terms']
    list_filter = ['plan', 'start_date', 'accepted_terms']
    search_fields = ['user__username', 'user__email', 'tc_or_vergi_no']
    readonly_fields = ['start_date']

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['user', 'package', 'amount', 'status', 'order_id', 'created_at']
    list_filter = ['status', 'package', 'payment_method', 'created_at']
    search_fields = ['user__username', 'user__email', 'order_id', 'transaction_id']
    readonly_fields = ['created_at', 'updated_at', 'param_response']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Temel Bilgiler', {
            'fields': ('user', 'package', 'amount', 'currency', 'status')
        }),
        ('Ödeme Detayları', {
            'fields': ('order_id', 'transaction_id', 'payment_method', 'created_at', 'updated_at')
        }),
        ('Hata Bilgileri', {
            'fields': ('error_message',),
            'classes': ('collapse',)
        }),
        ('Param Pos Bilgileri', {
            'fields': ('param_hash', 'param_response'),
            'classes': ('collapse',)
        }),
    )

# ==========================
# GENİŞLETİLMİŞ MEVZUAT ADMİN
# ==========================

@admin.register(MevzuatTuru)
class MevzuatTuruAdmin(admin.ModelAdmin):
    list_display = ['ad', 'kod', 'kategori', 'aktif', 'sira']
    list_filter = ['kategori', 'aktif']
    search_fields = ['ad', 'kod']
    ordering = ['sira', 'ad']

@admin.register(MevzuatKategori)
class MevzuatKategoriAdmin(admin.ModelAdmin):
    list_display = ['ad', 'kod', 'ust_kategori', 'aktif']
    list_filter = ['aktif', 'ust_kategori']
    search_fields = ['ad', 'kod']
    ordering = ['ad']

class MevzuatMaddeInline(admin.TabularInline):
    model = MevzuatMadde
    extra = 0
    fields = ['madde_no', 'madde_basligi', 'metin', 'aktif']
    ordering = ['sira', 'madde_no']

class MevzuatDegisiklikInline(admin.TabularInline):
    model = MevzuatDegisiklik
    fk_name = 'mevzuat'
    extra = 0
    fields = ['degisiklik_turu', 'aciklama', 'degistiren_mevzuat', 'degisiklik_tarihi']
    readonly_fields = ['kayit_tarihi']

@admin.register(MevzuatGelismis)
class MevzuatGelismisAdmin(admin.ModelAdmin):
    list_display = [
        'baslik', 'mevzuat_turu', 'mevzuat_numarasi', 
        'yayin_tarihi', 'durum', 'kayit_tarihi'
    ]
    list_filter = [
        'mevzuat_turu', 'durum', 'kategori', 
        'yayin_tarihi', 'kayit_tarihi'
    ]
    search_fields = [
        'baslik', 'mevzuat_numarasi', 'konu', 
        'anahtar_kelimeler', 'mevzuat_gov_tr_id'
    ]
    readonly_fields = ['kayit_tarihi', 'guncelleme_tarihi']
    
    fieldsets = (
        ('Temel Bilgiler', {
            'fields': ('baslik', 'mevzuat_turu', 'kategori', 'durum')
        }),
        ('Numaralandırma', {
            'fields': ('mevzuat_numarasi', 'sira_numarasi')
        }),
        ('Tarihler', {
            'fields': (
                'yayin_tarihi', 'yurutulme_tarihi', 'yurutulme_bitis_tarihi',
                'resmi_gazete_tarihi', 'resmi_gazete_sayisi', 'mukerrer_sayisi'
            )
        }),
        ('İçerik', {
            'fields': ('konu', 'ozet', 'anahtar_kelimeler', 'tam_metin')
        }),
        ('Dosya & HTML', {
            'fields': ('dosya', 'tam_metin_html'),
            'classes': ('collapse',)
        }),
        ('İlişkiler', {
            'fields': ('ilgili_mevzuatlar',),
            'classes': ('collapse',)
        }),
        ('Sistem', {
            'fields': (
                'kaynak_url', 'mevzuat_gov_tr_id', 
                'kayit_tarihi', 'guncelleme_tarihi', 'son_kontrol_tarihi'
            ),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [MevzuatMaddeInline, MevzuatDegisiklikInline]
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'mevzuat_turu', 'kategori'
        )

@admin.register(MevzuatMadde)
class MevzuatMaddeAdmin(admin.ModelAdmin):
    list_display = [
        'mevzuat', 'madde_no', 'madde_basligi', 
        'bent_no', 'fıkra_no', 'aktif'
    ]
    list_filter = ['aktif', 'mevzuat__mevzuat_turu']
    search_fields = [
        'madde_no', 'madde_basligi', 'metin', 
        'mevzuat__baslik'
    ]
    ordering = ['mevzuat', 'sira', 'madde_no']
    
    fieldsets = (
        ('Madde Bilgileri', {
            'fields': ('mevzuat', 'madde_no', 'madde_basligi', 'ust_madde')
        }),
        ('Hiyerarşi', {
            'fields': ('bent_no', 'fıkra_no', 'sira')
        }),
        ('İçerik', {
            'fields': ('metin', 'metin_html')
        }),
        ('Durum', {
            'fields': ('aktif',)
        }),
    )

@admin.register(MevzuatDegisiklik)
class MevzuatDegisiklikAdmin(admin.ModelAdmin):
    list_display = [
        'mevzuat', 'degisiklik_turu', 'degistiren_mevzuat',
        'degisiklik_tarihi', 'yurutulme_tarihi'
    ]
    list_filter = [
        'degisiklik_turu', 'degisiklik_tarihi', 
        'yurutulme_tarihi'
    ]
    search_fields = [
        'mevzuat__baslik', 'degistiren_mevzuat__baslik', 
        'aciklama'
    ]
    ordering = ['-degisiklik_tarihi']
    
    fieldsets = (
        ('Değişiklik Bilgileri', {
            'fields': ('mevzuat', 'degisiklik_turu', 'aciklama')
        }),
        ('Değiştiren', {
            'fields': ('degistiren_mevzuat',)
        }),
        ('Etkilenen Alanlar', {
            'fields': ('etkilenen_maddeler',)
        }),
        ('Tarihler', {
            'fields': ('degisiklik_tarihi', 'yurutulme_tarihi')
        }),
    )

@admin.register(MevzuatLog)
class MevzuatLogAdmin(admin.ModelAdmin):
    list_display = [
        'islem_turu', 'mevzuat', 'kullanici', 
        'ip_adresi', 'kayit_tarihi'
    ]
    list_filter = [
        'islem_turu', 'kayit_tarihi'
    ]
    search_fields = [
        'aciklama', 'mevzuat__baslik', 
        'kullanici__username'
    ]
    readonly_fields = ['kayit_tarihi']
    ordering = ['-kayit_tarihi']
    
    fieldsets = (
        ('İşlem Bilgileri', {
            'fields': ('islem_turu', 'aciklama')
        }),
        ('İlişkiler', {
            'fields': ('mevzuat', 'kullanici')
        }),
        ('Sistem', {
            'fields': ('ip_adresi', 'detaylar', 'kayit_tarihi')
        }),
    )
# Profesyonel Mevzuat Sistemi Admin Paneli
# core/admin.py dosyasına eklenecek

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count
from .models import (
    LegislationType, LegislationCategory, ProfessionalLegislation, 
    LegislationArticle, CourtDecisionLegislationRelation
)

# ========================
# MEVZUAT TÜRÜ YÖNETİMİ
# ========================

@admin.register(LegislationType)
class LegislationTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'hierarchy_level', 'legislation_count', 'color_preview', 'is_active']
    list_filter = ['is_active', 'hierarchy_level']
    search_fields = ['name', 'code']
    ordering = ['hierarchy_level', 'display_order']
    
    def legislation_count(self, obj):
        count = obj.professionallegislation_set.count()
        return format_html('<span class="badge">{}</span>', count)
    legislation_count.short_description = 'Mevzuat Sayısı'
    
    def color_preview(self, obj):
        return format_html(
            '<div style="width: 20px; height: 20px; background-color: {}; border-radius: 50%;"></div>',
            obj.color_code
        )
    color_preview.short_description = 'Renk'

# ========================
# KATEGORİ YÖNETİMİ
# ========================

@admin.register(LegislationCategory)
class LegislationCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'parent_category', 'legislation_count', 'color_preview', 'is_active']
    list_filter = ['is_active', 'parent_category']
    search_fields = ['name', 'code']
    ordering = ['display_order', 'name']
    prepopulated_fields = {'slug': ('name',)}
    
    def legislation_count(self, obj):
        count = obj.professionallegislation_set.count()
        return format_html('<span class="badge">{}</span>', count)
    legislation_count.short_description = 'Mevzuat Sayısı'
    
    def color_preview(self, obj):
        return format_html(
            '<div style="width: 20px; height: 20px; background-color: {}; border-radius: 50%;"></div>',
            obj.color_code
        )
    color_preview.short_description = 'Renk'

# ========================
# MADDE YÖNETİMİ (INLINE)
# ========================

class LegislationArticleInline(admin.TabularInline):
    model = LegislationArticle
    extra = 1
    fields = ['article_number', 'title', 'text', 'is_active', 'order']
    ordering = ['order', 'article_number']

# ========================
# PROFESYONEL MEVZUAT YÖNETİMİ
# ========================

@admin.register(ProfessionalLegislation)
class ProfessionalLegislationAdmin(admin.ModelAdmin):
    list_display = [
        'title_short', 'number', 'legislation_type', 'category', 
        'status_badge', 'article_count', 'view_count', 'effective_date'
    ]
    list_filter = [
        'legislation_type', 'category', 'status', 'is_verified',
        'effective_date', 'created_at'
    ]
    search_fields = ['title', 'number', 'keywords']
    ordering = ['-created_at']
    
    # Form alanları
    fieldsets = (
        ('Temel Bilgiler', {
            'fields': ('title', 'short_title', 'number', 'legislation_type', 'category')
        }),
        ('Tarihler', {
            'fields': (
                'publication_date', 'effective_date', 'expiry_date', 'acceptance_date',
                'official_gazette_date', 'official_gazette_number', 'duplicate_number'
            ),
            'classes': ('collapse',)
        }),
        ('İçerik', {
            'fields': ('subject', 'summary', 'keywords', 'full_text', 'full_text_html')
        }),
        ('Durum ve İlişkiler', {
            'fields': ('status', 'superseded_by', 'related_legislations')
        }),
        ('Kaynak ve SEO', {
            'fields': (
                'source_url', 'pdf_url', 'mevzuat_gov_id', 
                'slug', 'meta_description'
            ),
            'classes': ('collapse',)
        }),
        ('Veri Kalitesi', {
            'fields': (
                'is_verified', 'verification_date', 'data_quality_score',
                'last_checked'
            ),
            'classes': ('collapse',)
        })
    )
    
    # Readonly fields
    readonly_fields = ['slug', 'created_at', 'updated_at', 'view_count', 'search_count']
    
    # Inline
    inlines = [LegislationArticleInline]
    
    # Filter horizontal for many-to-many
    filter_horizontal = ['related_legislations']
    
    # Custom methods
    def title_short(self, obj):
        title = obj.title
        if len(title) > 60:
            return title[:60] + "..."
        return title
    title_short.short_description = 'Başlık'
    
    def status_badge(self, obj):
        colors = {
            'active': '#28a745',
            'repealed': '#dc3545', 
            'amended': '#ffc107',
            'suspended': '#6c757d'
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Durum'
    
    def article_count(self, obj):
        count = obj.articles.count()
        if count > 0:
            url = reverse('admin:core_legislationarticle_changelist') + f'?legislation={obj.id}'
            return format_html('<a href="{}" class="button">{} madde</a>', url, count)
        return "0 madde"
    article_count.short_description = 'Maddeler'
    
    # Actions
    actions = ['mark_as_verified', 'mark_as_active', 'mark_as_repealed']
    
    def mark_as_verified(self, request, queryset):
        from django.utils import timezone
        queryset.update(is_verified=True, verification_date=timezone.now())
        self.message_user(request, f'{queryset.count()} mevzuat doğrulandı.')
    mark_as_verified.short_description = 'Seçili mevzuatları doğrulandı olarak işaretle'
    
    def mark_as_active(self, request, queryset):
        queryset.update(status='active')
        self.message_user(request, f'{queryset.count()} mevzuat aktif yapıldı.')
    mark_as_active.short_description = 'Seçili mevzuatları aktif yap'
    
    def mark_as_repealed(self, request, queryset):
        queryset.update(status='repealed')
        self.message_user(request, f'{queryset.count()} mevzuat yürürlükten kaldırıldı.')
    mark_as_repealed.short_description = 'Seçili mevzuatları yürürlükten kaldır'

# ========================
# MADDE YÖNETİMİ
# ========================

@admin.register(LegislationArticle)
class LegislationArticleAdmin(admin.ModelAdmin):
    list_display = [
        'legislation_title', 'article_number', 'title_short', 
        'is_active', 'is_repealed', 'view_count', 'order'
    ]
    list_filter = [
        'legislation__legislation_type', 'legislation__category',
        'is_active', 'is_repealed', 'legislation'
    ]
    search_fields = ['legislation__title', 'article_number', 'title', 'text']
    ordering = ['legislation', 'order', 'article_number']
    
    # Form alanları
    fields = [
        'legislation', 'article_number', 'title', 'text', 'text_html',
        'footnotes', 'legal_notes', 'order', 'is_active', 'is_repealed', 'repeal_date'
    ]
    
    def legislation_title(self, obj):
        return f"{obj.legislation.number} - {obj.legislation.title[:50]}..."
    legislation_title.short_description = 'Mevzuat'
    
    def title_short(self, obj):
        if obj.title:
            return obj.title[:50] + "..." if len(obj.title) > 50 else obj.title
        return "Başlıksız"
    title_short.short_description = 'Madde Başlığı'
    
    # Actions
    actions = ['activate_articles', 'deactivate_articles']
    
    def activate_articles(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, f'{queryset.count()} madde aktif yapıldı.')
    activate_articles.short_description = 'Seçili maddeleri aktif yap'
    
    def deactivate_articles(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f'{queryset.count()} madde pasif yapıldı.')
    deactivate_articles.short_description = 'Seçili maddeleri pasif yap'

# ========================
# KARAR-MEVZUAT İLİŞKİSİ YÖNETİMİ
# ========================

@admin.register(CourtDecisionLegislationRelation)
class CourtDecisionLegislationRelationAdmin(admin.ModelAdmin):
    list_display = [
        'court_decision_short', 'legislation_short', 'article_number', 
        'relation_type', 'confidence_score', 'is_verified', 'created_at'
    ]
    list_filter = [
        'relation_type', 'is_verified', 'legislation__legislation_type',
        'created_at'
    ]
    search_fields = [
        'court_decision__karar_numarasi', 'legislation__title', 
        'article__article_number'
    ]
    ordering = ['-created_at']
    
    def court_decision_short(self, obj):
        return f"{obj.court_decision.karar_numarasi or 'No: Yok'}"
    court_decision_short.short_description = 'Karar'
    
    def legislation_short(self, obj):
        return f"{obj.legislation.number} - {obj.legislation.title[:30]}..."
    legislation_short.short_description = 'Mevzuat'
    
    def article_number(self, obj):
        return f"Madde {obj.article.article_number}" if obj.article else "-"
    article_number.short_description = 'Madde'

# ========================
# ADMIN SİTE ÖZELLEŞTİRMESİ
# ========================

admin.site.site_header = "LexaTech Mevzuat Yönetim Sistemi"
admin.site.site_title = "LexaTech Admin"
admin.site.index_title = "Mevzuat ve Yargı Kararları Yönetimi"

# Custom CSS ekle
admin.site.add_css = """
<style>
.badge {
    background-color: #007bff;
    color: white;
    padding: 2px 6px;
    border-radius: 10px;
    font-size: 11px;
}
.button {
    background: #007bff;
    color: white;
    padding: 4px 8px;
    text-decoration: none;
    border-radius: 4px;
    font-size: 12px;
}
.button:hover {
    background: #0056b3;
    color: white;
}
</style>
"""