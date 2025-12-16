"""
Bildirim servisi - Tüm bildirim işlemlerini merkezi olarak yönetir
"""
from django.utils import timezone
from django.contrib.auth.models import User
from .models import Notification, Payment, Subscription, UserProfile
from django.core.mail import send_mail
from django.conf import settings


class NotificationService:
    """Bildirim işlemlerini yöneten servis"""
    
    @staticmethod
    def create_purchase_notification(user, payment, package_name):
        """Paket satın alma bildirimi oluştur"""
        # Kullanıcı için bildirim
        user_notification = Notification.objects.create(
            notification_type='purchase',
            title='Paket Satın Alma Başarılı',
            message=f'{package_name} paketini başarıyla satın aldınız. Ödeme tutarı: {payment.amount} TL. Sipariş No: {payment.order_id}',
            user=user,
            payment=payment,
            extra_data={
                'package': package_name,
                'amount': str(payment.amount),
                'order_id': payment.order_id
            }
        )
        
        # Admin için bildirim
        admin_notification = Notification.objects.create(
            notification_type='purchase',
            title='Yeni Paket Satın Alma',
            message=f'Kullanıcı {user.username} ({user.email}) {package_name} paketini satın aldı. Tutar: {payment.amount} TL. Sipariş: {payment.order_id}',
            is_admin_notification=True,
            payment=payment,
            extra_data={
                'user_id': user.id,
                'username': user.username,
                'email': user.email,
                'package': package_name,
                'amount': str(payment.amount),
                'order_id': payment.order_id,
                'phone': getattr(user.profile, 'phone_number', 'N/A') if hasattr(user, 'profile') else 'N/A'
            }
        )
        
        # E-posta gönder
        user_notification.send_email_notification()
        
        return user_notification, admin_notification
    
    @staticmethod
    def create_expiry_warning_notification(user, subscription, days_left):
        """Abonelik sona erme uyarısı"""
        notification = Notification.objects.create(
            notification_type='expiry_warning',
            title=f'Aboneliğiniz {days_left} Gün Sonra Sona Eriyor',
            message=f'Sayın {user.username}, aboneliğiniz {subscription.end_date.strftime("%d.%m.%Y")} tarihinde sona erecek. Kesintisiz hizmet almaya devam etmek için aboneliğinizi yenileyebilirsiniz.',
            user=user,
            subscription=subscription,
            extra_data={
                'days_left': days_left,
                'end_date': subscription.end_date.isoformat(),
                'plan': subscription.plan
            }
        )
        
        notification.send_email_notification()
        return notification
    
    @staticmethod
    def create_expiry_notification(user, subscription):
        """Abonelik sona erdi bildirimi"""
        notification = Notification.objects.create(
            notification_type='expiry',
            title='Aboneliğiniz Sona Erdi',
            message=f'Sayın {user.username}, aboneliğiniz sona ermiştir. Servise erişmeye devam etmek için yeni bir paket satın alabilirsiniz.',
            user=user,
            subscription=subscription,
            extra_data={
                'end_date': subscription.end_date.isoformat(),
                'plan': subscription.plan
            }
        )
        
        notification.send_email_notification()
        return notification
    
    @staticmethod
    def create_free_trial_warning(user, profile, days_left):
        """Ücretsiz deneme sona erme uyarısı"""
        notification = Notification.objects.create(
            notification_type='free_trial_warning',
            title=f'Ücretsiz Denemeniz {days_left} Gün Sonra Sona Eriyor',
            message=f'Sayın {user.username}, 30 günlük ücretsiz deneme süreniz {profile.free_trial_end.strftime("%d.%m.%Y")} tarihinde sona erecek. Kesintisiz erişim için bir paket satın alabilirsiniz.',
            user=user,
            extra_data={
                'days_left': days_left,
                'trial_end_date': profile.free_trial_end.isoformat()
            }
        )
        
        notification.send_email_notification()
        return notification
    
    @staticmethod
    def create_free_trial_expired_notification(user, profile):
        """Ücretsiz deneme sona erdi bildirimi"""
        notification = Notification.objects.create(
            notification_type='free_trial_expired',
            title='Ücretsiz Denemeniz Sona Erdi',
            message=f'Sayın {user.username}, 30 günlük ücretsiz deneme süreniz sona ermiştir. Platforma erişmeye devam etmek için bir paket satın alabilirsiniz.',
            user=user,
            extra_data={
                'trial_end_date': profile.free_trial_end.isoformat()
            }
        )
        
        notification.send_email_notification()
        return notification
    
    @staticmethod
    def get_unread_notifications_count(user):
        """Kullanıcının okunmamış bildirim sayısı"""
        return Notification.objects.filter(
            user=user,
            is_read=False
        ).count()
    
    @staticmethod
    def get_admin_notifications():
        """Admin bildirimleri"""
        return Notification.objects.filter(
            is_admin_notification=True,
            is_read=False
        ).order_by('-created_at')
    
    @staticmethod
    def mark_admin_notifications_read():
        """Tüm admin bildirimleri okundu işaretle"""
        Notification.objects.filter(
            is_admin_notification=True,
            is_read=False
        ).update(is_read=True, read_at=timezone.now())
    
    @staticmethod
    def send_admin_email_summary():
        """Admin'e günlük özet e-posta gönder"""
        try:
            # Son 24 saatteki bildirimler
            last_24h = timezone.now() - timezone.timedelta(days=1)
            recent_notifications = Notification.objects.filter(
                is_admin_notification=True,
                created_at__gte=last_24h
            )
            
            if recent_notifications.exists():
                purchases = recent_notifications.filter(notification_type='purchase')
                
                message = f"""
Lexatech Platform - Günlük Özet

Son 24 saatte:
- {purchases.count()} yeni paket satışı
- Toplam bildirim: {recent_notifications.count()}

Paket Satışları:
"""
                
                for purchase in purchases:
                    extra = purchase.extra_data or {}
                    message += f"""
- Kullanıcı: {extra.get('username', 'N/A')} ({extra.get('email', 'N/A')})
  Paket: {extra.get('package', 'N/A')}
  Tutar: {extra.get('amount', 'N/A')} TL
  Telefon: {extra.get('phone', 'N/A')}
  Tarih: {purchase.created_at.strftime('%d.%m.%Y %H:%M')}
"""
                
                send_mail(
                    subject='Lexatech - Günlük Özet',
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[settings.ADMIN_EMAIL] if hasattr(settings, 'ADMIN_EMAIL') else ['lexatech.ai@gmail.com'],
                    fail_silently=False,
                )
                return True
        except Exception as e:
            print(f"Admin özet e-posta gönderme hatası: {str(e)}")
            return False
        
        return False