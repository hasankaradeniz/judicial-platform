# core/admin.py
from django.contrib import admin
from .models import (
    JudicialDecision, Article, Legislation,
    MevzuatTuru, MevzuatKategori, MevzuatGelismis, 
    MevzuatMadde, MevzuatDegisiklik, MevzuatLog,
    Subscription, Payment, UserProfile, Notification
)

# JudicialDecision için özelleştirilmiş admin
@admin.register(JudicialDecision)
class JudicialDecisionAdmin(admin.ModelAdmin):
    list_display = ['karar_numarasi', 'karar_turu', 'detected_legal_area', 'karar_tarihi', 'mahkeme_adi']
    list_filter = ['karar_turu', 'detected_legal_area', 'karar_tarihi']
    search_fields = ['karar_numarasi', 'esas_numarasi', 'mahkeme_adi', 'karar_metni']
    readonly_fields = ['detected_legal_area']
    date_hierarchy = 'karar_tarihi'
    ordering = ['-karar_tarihi']
    
    fieldsets = (
        ('Temel Bilgiler', {
            'fields': ('karar_turu', 'karar_veren_mahkeme', 'mahkeme_adi')
        }),
        ('Numara ve Tarihler', {
            'fields': ('esas_numarasi', 'karar_numarasi', 'karar_no', 'karar_tarihi')
        }),
        ('AI Kategorilendirme', {
            'fields': ('detected_legal_area',),
            'description': 'AI tarafından otomatik tespit edilen hukuk alanı'
        }),
        ('İçerik', {
            'fields': ('dava_konusu', 'karar_ozeti', 'karar_metni', 'anahtar_kelimeler')
        }),
        ('Taraflar', {
            'fields': ('davaci', 'davali', 'mudahiller'),
            'classes': ('collapse',)
        }),
    )
    
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        
        # AI kategorilendirme istatistikleri
        from django.db.models import Count
        total = JudicialDecision.objects.count()
        categorized = JudicialDecision.objects.exclude(detected_legal_area__isnull=True).exclude(detected_legal_area='').count()
        
        extra_context['ai_stats'] = {
            'total': total,
            'categorized': categorized,
            'percentage': (categorized/total*100) if total > 0 else 0
        }
        
        # En popüler hukuk alanları
        top_areas = JudicialDecision.objects.exclude(
            detected_legal_area__isnull=True
        ).exclude(
            detected_legal_area=''
        ).values('detected_legal_area').annotate(
            count=Count('id')
        ).order_by('-count')[:5]
        
        extra_context['top_areas'] = top_areas
        
        return super().changelist_view(request, extra_context=extra_context)

admin.site.register(Article)
admin.site.register(Legislation)
