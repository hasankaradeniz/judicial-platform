"""
Management command to check for expiring subscriptions and send notifications
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from core.models import Subscription, UserProfile, Notification
from core.notification_service import NotificationService


class Command(BaseCommand):
    help = 'Check for expiring subscriptions and free trials, send notifications'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--send-admin-summary',
            action='store_true',
            help='Send admin daily summary email',
        )
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Checking expiring subscriptions...'))
        
        now = timezone.now()
        
        # 3 gün içinde bitecek abonelikler
        warning_date_3 = now + timedelta(days=3)
        expiring_subscriptions_3 = Subscription.objects.filter(
            end_date__lte=warning_date_3,
            end_date__gt=now
        )
        
        # 7 gün içinde bitecek abonelikler
        warning_date_7 = now + timedelta(days=7)
        expiring_subscriptions_7 = Subscription.objects.filter(
            end_date__lte=warning_date_7,
            end_date__gt=warning_date_3
        )
        
        # 3 gün içinde bitecek abonelikler için uyarı
        for subscription in expiring_subscriptions_3:
            days_left = (subscription.end_date - now).days
            
            # Bu abonelik için bu süre için uyarı gönderilmiş mi kontrol et
            existing_warning = Notification.objects.filter(
                user=subscription.user,
                notification_type='expiry_warning',
                subscription=subscription,
                created_at__gte=now - timedelta(days=1)  # Son 24 saatte
            ).exists()
            
            if not existing_warning:
                NotificationService.create_expiry_warning_notification(
                    user=subscription.user,
                    subscription=subscription,
                    days_left=days_left
                )
                self.stdout.write(
                    self.style.WARNING(
                        f'Expiry warning sent to {subscription.user.username} ({days_left} days left)'
                    )
                )
        
        # 7 gün içinde bitecek abonelikler için uyarı (sadece bir kez)
        for subscription in expiring_subscriptions_7:
            days_left = (subscription.end_date - now).days
            
            # Bu abonelik için 7 günlük uyarı gönderilmiş mi kontrol et
            existing_warning = Notification.objects.filter(
                user=subscription.user,
                notification_type='expiry_warning',
                subscription=subscription,
                extra_data__days_left=days_left
            ).exists()
            
            if not existing_warning:
                NotificationService.create_expiry_warning_notification(
                    user=subscription.user,
                    subscription=subscription,
                    days_left=days_left
                )
                self.stdout.write(
                    self.style.WARNING(
                        f'Expiry warning sent to {subscription.user.username} ({days_left} days left)'
                    )
                )
        
        # Ücretsiz deneme süreleri kontrol et
        self.stdout.write(self.style.SUCCESS('Checking expiring free trials...'))
        
        # 3 gün içinde bitecek ücretsiz denemeler
        trial_warning_date_3 = now + timedelta(days=3)
        expiring_trials_3 = UserProfile.objects.filter(
            is_free_trial=True,
            free_trial_end__lte=trial_warning_date_3,
            free_trial_end__gt=now
        )
        
        # 7 gün içinde bitecek ücretsiz denemeler  
        trial_warning_date_7 = now + timedelta(days=7)
        expiring_trials_7 = UserProfile.objects.filter(
            is_free_trial=True,
            free_trial_end__lte=trial_warning_date_7,
            free_trial_end__gt=trial_warning_date_3
        )
        
        # 3 gün içinde bitecek ücretsiz denemeler için uyarı
        for profile in expiring_trials_3:
            days_left = (profile.free_trial_end - now).days
            
            existing_warning = Notification.objects.filter(
                user=profile.user,
                notification_type='free_trial_warning',
                created_at__gte=now - timedelta(days=1)
            ).exists()
            
            if not existing_warning:
                NotificationService.create_free_trial_warning(
                    user=profile.user,
                    profile=profile,
                    days_left=days_left
                )
                self.stdout.write(
                    self.style.WARNING(
                        f'Free trial warning sent to {profile.user.username} ({days_left} days left)'
                    )
                )
        
        # 7 gün içinde bitecek ücretsiz denemeler için uyarı
        for profile in expiring_trials_7:
            days_left = (profile.free_trial_end - now).days
            
            existing_warning = Notification.objects.filter(
                user=profile.user,
                notification_type='free_trial_warning',
                extra_data__days_left=days_left
            ).exists()
            
            if not existing_warning:
                NotificationService.create_free_trial_warning(
                    user=profile.user,
                    profile=profile,
                    days_left=days_left
                )
                self.stdout.write(
                    self.style.WARNING(
                        f'Free trial warning sent to {profile.user.username} ({days_left} days left)'
                    )
                )
        
        # Admin özet e-posta gönder
        if options['send_admin_summary']:
            self.stdout.write(self.style.SUCCESS('Sending admin summary email...'))
            if NotificationService.send_admin_email_summary():
                self.stdout.write(self.style.SUCCESS('Admin summary email sent successfully'))
            else:
                self.stdout.write(self.style.WARNING('No new notifications for admin summary'))
        
        self.stdout.write(self.style.SUCCESS('Expiring subscription check completed'))