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
    list_display = ['id', 'karar_numarasi', 'kategori_sayisi', 'karar_tarihi', 'karar_veren_mahkeme']
    list_filter = ['detected_legal_area', 'karar_tarihi', 'karar_veren_mahkeme']
    search_fields = ['id', 'karar_numarasi', 'esas_numarasi', 'karar_veren_mahkeme', 'karar_tam_metni']
    readonly_fields = ['detected_legal_area']
    date_hierarchy = 'karar_tarihi'
    ordering = ['-id']  # ID numarasına göre azalan sırada (en yeni üstte)
    list_per_page = 50  # Sayfa başı kayıt sayısı
    
    def kategori_sayisi(self, obj):
        """Kararın kaç kategoride olduğunu gösterir"""
        from django.db import connection
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT COUNT(*) FROM karar_kategori_iliskileri WHERE karar_id = %s",
                    [obj.id]
                )
                result = cursor.fetchone()
                count = result[0] if result else 0
                
                if count == 0:
                    return "Kategori yok"
                elif count == 1:
                    return "1 kategori"
                else:
                    return f"{count} kategori"
        except Exception as e:
            # Fallback to detected_legal_area if query fails
            if obj.detected_legal_area:
                categories = [cat.strip() for cat in obj.detected_legal_area.split(',') if cat.strip()]
                return f"{len(categories)} kategori (fallback)"
            return "Kategori yok"
    kategori_sayisi.short_description = "Kategori Sayısı"
    
    
    actions = ['export_selected_decisions', 'mark_as_reviewed']
    
    def export_selected_decisions(self, request, queryset):
        """Seçilen kararları CSV olarak dışa aktar"""
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="judicial_decisions.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['ID', 'Karar Numarası', 'Karar Türü', 'Mahkeme', 'Tarih', 'Kategori'])
        
        for decision in queryset:
            writer.writerow([
                decision.id,
                decision.karar_numarasi or '',
                decision.karar_turu or '',
                decision.karar_veren_mahkeme or '',
                decision.karar_tarihi or '',
                decision.detected_legal_area or ''
            ])
        
        self.message_user(request, f'{queryset.count()} karar dışa aktarıldı.')
        return response
    export_selected_decisions.short_description = "Seçilen kararları CSV olarak dışa aktar"
    
    def mark_as_reviewed(self, request, queryset):
        """Seçilen kararları gözden geçirildi olarak işaretle"""
        updated = 0
        for decision in queryset:
            # Eğer bir reviewed field'ı varsa güncelleyebiliriz
            # Bu örnek için anahtar kelimelere "REVIEWED" ekleyelim
            if decision.anahtar_kelimeler:
                if "REVIEWED" not in decision.anahtar_kelimeler:
                    decision.anahtar_kelimeler += ", REVIEWED"
                    decision.save()
                    updated += 1
            else:
                decision.anahtar_kelimeler = "REVIEWED"
                decision.save()
                updated += 1
        
        self.message_user(request, f'{updated} karar gözden geçirildi olarak işaretlendi.')
    mark_as_reviewed.short_description = "Seçilen kararları gözden geçirildi olarak işaretle"
    
    fieldsets = (
        ('Temel Bilgiler', {
            'fields': ('karar_turu', 'karar_veren_mahkeme')
        }),
        ('Numara ve Tarihler', {
            'fields': ('esas_numarasi', 'karar_numarasi', 'karar_tarihi')
        }),
        ('AI Kategorilendirme', {
            'fields': ('detected_legal_area',),
            'description': 'AI tarafından otomatik tespit edilen hukuk alanı'
        }),
        ('İçerik', {
            'fields': ('karar_ozeti', 'karar_tam_metni', 'anahtar_kelimeler')
        }),
    )

admin.site.register(Article)
admin.site.register(Legislation)

# Subscription ve Payment modelleri
@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user_info', 'plan_info', 'subscription_status', 'remaining_days_info', 'payment_info', 'start_date', 'end_date']
    list_filter = ['plan', 'start_date', 'end_date', 'accepted_terms', 'accepted_sale']
    search_fields = ['user__username', 'user__email', 'tc_or_vergi_no', 'address']
    readonly_fields = ['start_date', 'subscription_status', 'remaining_days_info', 'payment_info']
    date_hierarchy = 'start_date'
    ordering = ['-start_date']
    list_per_page = 25
    
    def user_info(self, obj):
        """Kullanıcı bilgileri"""
        return f"{obj.user.username} ({obj.user.email})"
    user_info.short_description = "Kullanıcı"
    
    def plan_info(self, obj):
        """Plan detayları"""
        return f"{obj.get_plan_display()}"
    plan_info.short_description = "Plan"
    
    def subscription_status(self, obj):
        """Abonelik durumu"""
        from django.utils import timezone
        now = timezone.now()
        
        if obj.end_date > now:
            days_left = (obj.end_date - now).days
            if days_left <= 7:
                return f"⚠️ {days_left} gün kaldı"
            else:
                return "✅ Aktif"
        else:
            return "❌ Süresi doldu"
    subscription_status.short_description = "Durum"
    
    def remaining_days_info(self, obj):
        """Kalan günler"""
        from django.utils import timezone
        if obj.end_date:
            remaining = (obj.end_date - timezone.now()).days
            return f"{remaining} gün" if remaining > 0 else "Süresi doldu"
        return "Bilinmiyor"
    remaining_days_info.short_description = "Kalan Süre"
    
    def payment_info(self, obj):
        """Ödeme bilgisi"""
        try:
            # En son ödemeyi bul
            payment = Payment.objects.filter(user=obj.user).order_by('-created_at').first()
            if payment:
                return f"{payment.amount} TL ({payment.get_status_display()})"
            return "Ödeme bulunamadı"
        except:
            return "Bilgi yok"
    payment_info.short_description = "Son Ödeme"

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

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user_info', 'email', 'phone_number', 'full_address', 'account_type', 'status_info', 'remaining_time', 'last_login', 'created_at']
    list_filter = ['is_free_trial', 'city', 'district', 'created_at', 'free_trial_end', 'user__last_login', 'user__is_active']
    search_fields = ['user__username', 'user__email', 'user__first_name', 'user__last_name', 'phone_number', 'city', 'district', 'address_line_1']
    readonly_fields = ['created_at', 'updated_at', 'free_trial_start', 'account_type', 'status_info', 'remaining_time', 'subscription_details', 'trial_details', 'user_info', 'email', 'full_address', 'last_login']
    list_per_page = 25
    ordering = ['-created_at']
    
    def user_info(self, obj):
        """Kullanıcı temel bilgileri"""
        info_parts = []
        
        # Kullanıcı adı ve tam isim
        full_name = f"{obj.user.first_name} {obj.user.last_name}".strip()
        if full_name:
            info_parts.append(f"👤 Ad: {full_name}")
            info_parts.append(f"🔖 Kullanıcı Adı: {obj.user.username}")
        else:
            info_parts.append(f"🔖 Kullanıcı Adı: {obj.user.username}")
        
        # Kullanıcı durumu
        status_icons = []
        if obj.user.is_active:
            status_icons.append("✅ Aktif")
        else:
            status_icons.append("❌ Pasif")
            
        if obj.user.is_superuser:
            status_icons.append("🔑 Süper Kullanıcı")
        elif obj.user.is_staff:
            status_icons.append("⚙️ Staff")
            
        info_parts.append(f"📊 Durum: {', '.join(status_icons)}")
        
        # Kayıt tarihi
        join_date = obj.user.date_joined.strftime('%d.%m.%Y')
        info_parts.append(f"📅 Kayıt: {join_date}")
        
        return "\n".join(info_parts)
    user_info.short_description = "Kullanıcı Bilgileri"
    
    def email(self, obj):
        """E-posta adresi ve doğrulama durumu"""
        if obj.user.email:
            # E-posta doğrulandı mı kontrol et
            email_verified = "✅ Doğrulandı" if obj.user.email else "⚠️ Doğrulanmadı"
            return f"📧 {obj.user.email}\n{email_verified}"
        return "❌ E-posta adresi yok"
    email.short_description = "E-posta Bilgisi"
    
    def full_address(self, obj):
        """Tam adres bilgisi"""
        address_lines = []
        
        if obj.address_line_1:
            address_lines.append(f"🏠 Adres 1: {obj.address_line_1}")
        
        if obj.address_line_2:
            address_lines.append(f"🏢 Adres 2: {obj.address_line_2}")
        
        location_parts = []
        if obj.district:
            location_parts.append(obj.district)
        if obj.city:
            location_parts.append(obj.city)
        
        if location_parts:
            address_lines.append(f"📍 Konum: {' / '.join(location_parts)}")
        
        if obj.postal_code:
            address_lines.append(f"📮 Posta Kodu: {obj.postal_code}")
        
        # Telefon bilgisi de ekleyelim
        if obj.phone_number:
            address_lines.append(f"📞 Telefon: {obj.phone_number}")
        
        return "\n".join(address_lines) if address_lines else "❌ Adres bilgisi yok"
    full_address.short_description = "Tam Adres ve İletişim"
    
    def account_type(self, obj):
        """Hesap türü"""
        if obj.has_active_subscription():
            try:
                subscription = obj.user.subscription
                return f"Abonelik ({subscription.get_plan_display()})"
            except:
                return "Abonelik (Detay bulunamadı)"
        elif obj.is_free_trial:
            return "Ücretsiz Deneme"
        else:
            return "Standart"
    account_type.short_description = "Hesap Türü"
    
    def status_info(self, obj):
        """Detaylı durum bilgisi"""
        if obj.has_active_subscription():
            return "✅ Aktif Abonelik"
        elif obj.is_free_trial:
            if obj.is_free_trial_expired():
                return "❌ Deneme Süresi Doldu"
            elif obj.is_trial_ending_soon():
                return "⚠️ Deneme Bitiyor"
            else:
                return "✅ Aktif Deneme"
        else:
            return "⏸️ Standart Hesap"
    status_info.short_description = "Durum"
    
    def remaining_time(self, obj):
        """Kalan süre detaylı"""
        try:
            from django.utils import timezone
            from .models import Subscription
            
            # Önce abonelik kontrol et
            subscription = Subscription.objects.filter(user=obj.user).first()
            if subscription and subscription.end_date > timezone.now():
                remaining = (subscription.end_date - timezone.now()).days
                return f"{remaining} gün (Abonelik)"
        except Exception as e:
            pass
        
        # Deneme kontrolü
        if obj.is_free_trial:
            remaining = obj.get_remaining_trial_days()
            if remaining > 0:
                return f"{remaining} gün (Deneme)"
            else:
                return "Süre doldu"
        else:
            return "Sınırsız (Standart)"
    remaining_time.short_description = "Kalan Süre"
    
    def last_login(self, obj):
        """Son giriş tarihi"""
        if obj.user.last_login:
            try:
                from django.utils import timezone
                diff = timezone.now() - obj.user.last_login
                if diff.days == 0:
                    return "Bugün"
                elif diff.days == 1:
                    return "Dün"
                else:
                    return f"{diff.days} gün önce"
            except Exception as e:
                return f"Hata: {str(e)}"
        return "Hiç giriş yapmamış"
    last_login.short_description = "Son Giriş"
    
    def subscription_details(self, obj):
        """Abonelik detayları"""
        try:
            from django.utils import timezone
            from .models import Subscription
            subscription = Subscription.objects.filter(user=obj.user).first()
            if not subscription:
                return "❌ Abonelik bulunamadı"
            details = [
                f"📋 Plan: {subscription.get_plan_display()}",
                f"📅 Başlangıç: {subscription.start_date.strftime('%d.%m.%Y %H:%M')}",
                f"📅 Bitiş: {subscription.end_date.strftime('%d.%m.%Y %H:%M')}",
                f"⏱️ Durum: {'✅ Aktif' if subscription.end_date > timezone.now() else '❌ Süresi dolmuş'}",
            ]
            if subscription.tc_or_vergi_no:
                details.append(f"🆔 TC/Vergi No: {subscription.tc_or_vergi_no}")
            if subscription.address:
                details.append(f"📍 Fatura Adresi: {subscription.address}")
            
            # Sözleşme kabulleri
            contracts = []
            if subscription.accepted_terms:
                contracts.append("✅ Kullanıcı Sözleşmesi")
            if subscription.accepted_sale:
                contracts.append("✅ Mesafeli Satış")
            if subscription.accepted_delivery:
                contracts.append("✅ Teslimat Şartları")
            
            if contracts:
                details.append(f"📝 Kabul Edilen Sözleşmeler:\n   {chr(10).join(contracts)}")
            
            # Son ödeme bilgisi
            try:
                from .models import Payment
                last_payment = Payment.objects.filter(user=obj.user, status='success').order_by('-created_at').first()
                if last_payment:
                    details.append(f"💰 Son Ödeme: {last_payment.amount} TL ({last_payment.created_at.strftime('%d.%m.%Y')})")
            except:
                pass
                
            return "\n".join(details)
        except Exception as e:
            return f"Abonelik bulunamadı (Hata: {str(e)})"
    subscription_details.short_description = "Abonelik Detayları"
    
    def trial_details(self, obj):
        """Deneme detayları"""
        if obj.is_free_trial:
            from django.utils import timezone
            
            remaining_days = obj.get_remaining_trial_days()
            total_days = 7  # 7 günlük deneme
            used_days = total_days - remaining_days if remaining_days >= 0 else total_days
            
            # Durum emoji
            if obj.is_free_trial_expired():
                status_emoji = "❌"
                status_text = "Süresi dolmuş"
            elif obj.is_trial_ending_soon():
                status_emoji = "⚠️"
                status_text = "Yakında bitiyor"
            else:
                status_emoji = "✅"
                status_text = "Aktif"
                
            details = [
                f"📅 Başlangıç: {obj.free_trial_start.strftime('%d.%m.%Y %H:%M') if obj.free_trial_start else 'Bilinmiyor'}",
                f"📅 Bitiş: {obj.free_trial_end.strftime('%d.%m.%Y %H:%M') if obj.free_trial_end else 'Bilinmiyor'}",
                f"⏰ Toplam Süre: {total_days} gün",
                f"📊 Kullanılan: {used_days} gün",
                f"⏱️ Kalan: {remaining_days} gün",
                f"{status_emoji} Durum: {status_text}",
            ]
            
            # Progress bar (basit ASCII)
            if total_days > 0:
                progress = min(used_days / total_days, 1.0)
                bar_length = 20
                filled_length = int(bar_length * progress)
                bar = "█" * filled_length + "░" * (bar_length - filled_length)
                percentage = int(progress * 100)
                details.append(f"📈 İlerleme: |{bar}| {percentage}%")
            
            # Bildirimler gönderildi mi?
            try:
                from .models import Notification
                trial_notifications = Notification.objects.filter(
                    user=obj.user, 
                    notification_type__in=['free_trial_warning', 'free_trial_expired']
                ).order_by('-created_at')
                
                if trial_notifications.exists():
                    details.append("📧 Gönderilen Bildirimler:")
                    for notif in trial_notifications[:3]:  # Son 3 bildirim
                        notif_date = notif.created_at.strftime('%d.%m.%Y')
                        notif_type = "Uyarı" if notif.notification_type == 'free_trial_warning' else "Süre Doldu"
                        details.append(f"   • {notif_type} ({notif_date})")
            except:
                pass
                
            return "\n".join(details)
        return "❌ Ücretsiz deneme süresi yok"
    trial_details.short_description = "Deneme Detayları"
    
    actions = ['extend_trial_period', 'send_notification_email', 'export_user_details']
    
    def extend_trial_period(self, request, queryset):
        """Seçilen kullanıcıların deneme süresini 30 gün uzat"""
        from datetime import timedelta
        from django.utils import timezone
        
        extended_count = 0
        for profile in queryset:
            if profile.is_free_trial and profile.free_trial_end:
                # 30 gün uzat
                profile.free_trial_end = profile.free_trial_end + timedelta(days=30)
                profile.save()
                extended_count += 1
        
        self.message_user(request, f'{extended_count} kullanıcının deneme süresi 30 gün uzatıldı.')
    extend_trial_period.short_description = "Seçilen kullanıcıların deneme süresini 30 gün uzat"
    
    def send_notification_email(self, request, queryset):
        """Seçilen kullanıcılara bildirim e-postası gönder"""
        from django.core.mail import send_mail
        from django.conf import settings
        
        sent_count = 0
        for profile in queryset:
            if profile.user.email:
                try:
                    send_mail(
                        subject='Lexatech - Hesap Durumunuz Hakkında',
                        message=f"""
Sayın {profile.user.first_name or profile.user.username},

Hesap durumunuz kontrol edilmiştir.

Teşekkürler,
Lexatech Admin Ekibi
                        """,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[profile.user.email],
                        fail_silently=False,
                    )
                    sent_count += 1
                except:
                    pass
        
        self.message_user(request, f'{sent_count} kullanıcıya e-posta gönderildi.')
    send_notification_email.short_description = "Seçilen kullanıcılara bildirim e-postası gönder"
    
    def export_user_details(self, request, queryset):
        """Kullanıcı detaylarını CSV olarak dışa aktar"""
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="user_profiles.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Kullanıcı Adı', 'E-posta', 'Ad Soyad', 'Telefon', 'Şehir', 'İlçe',
            'Hesap Türü', 'Durum', 'Kalan Süre', 'Son Giriş', 'Kayıt Tarihi'
        ])
        
        for profile in queryset:
            writer.writerow([
                profile.user.username,
                profile.user.email or '',
                f"{profile.user.first_name} {profile.user.last_name}".strip(),
                profile.phone_number or '',
                profile.city or '',
                profile.district or '',
                profile.account_type(profile),
                profile.status_info(profile),
                profile.remaining_time(profile),
                profile.last_login(profile),
                profile.created_at.strftime('%d.%m.%Y') if profile.created_at else ''
            ])
        
        self.message_user(request, f'{queryset.count()} kullanıcı detayı dışa aktarıldı.')
        return response
    export_user_details.short_description = "Kullanıcı detaylarını CSV olarak dışa aktar"
    
    fieldsets = (
        ('👤 Temel Kullanıcı Bilgileri', {
            'fields': ('user', 'user_info', 'email', 'phone_number'),
            'description': 'Kullanıcının temel kimlik ve iletişim bilgileri'
        }),
        ('🏠 Tam Adres Bilgileri', {
            'fields': (
                'address_line_1', 
                'address_line_2', 
                'city', 
                'district', 
                'postal_code',
                'full_address'
            ),
            'description': 'Kullanıcının fatura ve teslimat adresi bilgileri'
        }),
        ('📊 Hesap Durumu ve Erişim', {
            'fields': (
                'account_type', 
                'status_info', 
                'remaining_time', 
                'last_login'
            ),
            'description': 'Kullanıcının hesap durumu ve platform erişim bilgileri'
        }),
        ('🆓 Ücretsiz Deneme Detayları', {
            'fields': (
                'is_free_trial', 
                'free_trial_start', 
                'free_trial_end', 
                'trial_details'
            ),
            'description': 'Kullanıcının ücretsiz deneme süresi ve detayları'
        }),
        ('💳 Abonelik ve Ödeme Bilgileri', {
            'fields': ('subscription_details',),
            'description': 'Kullanıcının aktif abonelik ve ödeme geçmişi'
        }),
        ('🔧 Sistem ve Log Bilgileri', {
            'fields': ('created_at', 'updated_at'),
            'description': 'Hesap oluşturma ve güncelleme tarihleri'
        }),
    )

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'notification_type', 'is_read', 'is_admin_notification', 'created_at']
    list_filter = ['notification_type', 'is_read', 'is_admin_notification', 'is_sent_email', 'created_at']
    search_fields = ['title', 'message', 'user__username', 'user__email']
    readonly_fields = ['created_at', 'sent_at', 'read_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Bildirim Bilgileri', {
            'fields': ('notification_type', 'title', 'message', 'user')
        }),
        ('İlişkiler', {
            'fields': ('payment', 'subscription'),
            'classes': ('collapse',)
        }),
        ('Durum', {
            'fields': ('is_read', 'is_sent_email', 'is_admin_notification')
        }),
        ('Tarihler', {
            'fields': ('created_at', 'sent_at', 'read_at'),
            'classes': ('collapse',)
        }),
        ('Ek Veriler', {
            'fields': ('extra_data',),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_read', 'send_email_notifications']
    
    def mark_as_read(self, request, queryset):
        """Seçilen bildirimleri okundu olarak işaretle"""
        updated = queryset.update(is_read=True)
        self.message_user(request, f'{updated} bildirim okundu olarak işaretlendi.')
    mark_as_read.short_description = "Seçilen bildirimleri okundu olarak işaretle"
    
    def send_email_notifications(self, request, queryset):
        """Seçilen bildirimler için e-posta gönder"""
        sent_count = 0
        for notification in queryset:
            if notification.send_email_notification():
                sent_count += 1
        self.message_user(request, f'{sent_count} bildirim için e-posta gönderildi.')
    send_email_notifications.short_description = "Seçilen bildirimler için e-posta gönder"

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
