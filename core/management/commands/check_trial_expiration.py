from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from core.models import UserProfile, Notification
from datetime import timedelta

class Command(BaseCommand):
    help = 'Ücretsiz deneme süreleri kontrolü ve bildirim gönderimi'

    def handle(self, *args, **options):
        now = timezone.now()
        
        # 7 gün kala uyarı (henüz bildirilmemiş)
        seven_days_before = now + timedelta(days=7)
        trial_ending_users = UserProfile.objects.filter(
            is_free_trial=True,
            free_trial_end__lte=seven_days_before,
            free_trial_end__gt=now,
            user__is_active=True
        ).select_related('user')
        
        for profile in trial_ending_users:
            # Önceki bildirim var mı kontrol et
            existing_notification = Notification.objects.filter(
                user=profile.user,
                notification_type='free_trial_warning'
            ).first()
            
            if not existing_notification:
                remaining_days = (profile.free_trial_end - now).days
                
                # Notification oluştur
                notification = Notification.objects.create(
                    notification_type='free_trial_warning',
                    title='Ücretsiz Deneme Süreniz Bitiyor',
                    message=f'Ücretsiz deneme süreniz {remaining_days} gün sonra sona erecek. '
                           f'Kesintisiz hizmet için lütfen bir paket seçin.',
                    user=profile.user
                )
                
                # Email gönder
                if profile.user.email:
                    try:
                        send_mail(
                            subject='Ücretsiz Deneme Süreniz Bitiyor - Lexatech',
                            message=f"""
Sayın {profile.user.first_name or profile.user.username},

Ücretsiz deneme süreniz {remaining_days} gün sonra sona erecek.
Lexatech'in tüm özelliklerinden kesintisiz yararlanmak için lütfen bir paket seçin.

Paketlerimizi görüntülemek için: {settings.SITE_DOMAIN}/paketler/

Teşekkürler,
Lexatech Ekibi
                            """,
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            recipient_list=[profile.user.email],
                            fail_silently=False,
                        )
                        notification.is_sent_email = True
                        notification.sent_at = now
                        notification.save()
                        
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'Uyarı e-postası gönderildi: {profile.user.email}'
                            )
                        )
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f'E-posta gönderim hatası: {str(e)}')
                        )
        
        # Süresi dolan kullanıcılar
        expired_users = UserProfile.objects.filter(
            is_free_trial=True,
            free_trial_end__lt=now,
            user__is_active=True
        ).select_related('user')
        
        for profile in expired_users:
            # Önceki bildirim var mı kontrol et
            existing_notification = Notification.objects.filter(
                user=profile.user,
                notification_type='free_trial_expired'
            ).first()
            
            if not existing_notification:
                # Notification oluştur
                notification = Notification.objects.create(
                    notification_type='free_trial_expired',
                    title='Ücretsiz Deneme Süreniz Sona Erdi',
                    message='Ücretsiz deneme süreniz sona erdi. '
                           'Sistemimizi kullanmaya devam etmek için lütfen bir paket seçin.',
                    user=profile.user
                )
                
                # Email gönder
                if profile.user.email:
                    try:
                        send_mail(
                            subject='Ücretsiz Deneme Süreniz Sona Erdi - Lexatech',
                            message=f"""
Sayın {profile.user.first_name or profile.user.username},

Ücretsiz deneme süreniz sona erdi.
Lexatech'in tüm özelliklerinden yararlanmak için lütfen bir paket seçin.

Paketlerimizi görüntülemek için: {settings.SITE_DOMAIN}/paketler/

Teşekkürler,
Lexatech Ekibi
                            """,
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            recipient_list=[profile.user.email],
                            fail_silently=False,
                        )
                        notification.is_sent_email = True
                        notification.sent_at = now
                        notification.save()
                        
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'Süre doldu e-postası gönderildi: {profile.user.email}'
                            )
                        )
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f'E-posta gönderim hatası: {str(e)}')
                        )
        
        total_warned = trial_ending_users.count()
        total_expired = expired_users.count()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'İşlem tamamlandı. {total_warned} uyarı, {total_expired} süre doldu bildirimi.'
            )
        )