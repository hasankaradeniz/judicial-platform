"""
Middleware for handling user access control and expiry redirects
"""
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth.models import AnonymousUser
from .models import UserProfile
from .notification_service import NotificationService


class UserAccessControlMiddleware:
    """
    Kullanıcı erişim kontrolü ve süre dolmuş kullanıcıları yönlendirme middleware'i
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # Erişim kontrolü yapılmayacak URL'ler
        self.excluded_urls = [
            '/admin/',
            '/accounts/login/',
            '/accounts/logout/',
            '/register/',
            '/signup/',
            '/subscription/',
            '/payment/',
            '/demo-payment/',
            '/paketler/',
            '/about/',
            '/gizlilik-politikasi/',
            '/kullanici-sozlesmesi/',
            '/ziyaretci-veri-koruma/',
            '/static/',
            '/media/',
        ]
    
    def __call__(self, request):
        # Middleware işlemi
        response = self.process_request(request)
        if response:
            return response
        
        response = self.get_response(request)
        return response
    
    def process_request(self, request):
        """İstek işleme öncesi kontroller"""
        
        # Anonim kullanıcılar için kontrol yok
        if isinstance(request.user, AnonymousUser) or not request.user.is_authenticated:
            return None
        
        # Superuser'lar için kontrol yok
        if request.user.is_superuser or request.user.is_staff:
            return None
        
        # Hariç tutulan URL'ler için kontrol yok
        current_path = request.path
        for excluded_url in self.excluded_urls:
            if current_path.startswith(excluded_url):
                return None
        
        # UserProfile kontrol et
        try:
            profile = request.user.profile
        except UserProfile.DoesNotExist:
            # Profile yoksa oluştur
            from django.utils import timezone
            from datetime import timedelta
            profile = UserProfile.objects.create(
                user=request.user,
                phone_number='05555555555',  # Default phone number
                is_free_trial=True,
                free_trial_start=timezone.now(),
            )
            profile.free_trial_end = profile.free_trial_start + timedelta(days=30)
            profile.save()
        
        # Erişim kontrolü
        if not profile.can_access_platform():
            # Süre dolmuş kullanıcıyı paket satın alma sayfasına yönlendir
            
            # Bildirim oluştur (sadece bir kez)
            if profile.is_free_trial and profile.is_free_trial_expired():
                # Ücretsiz deneme süresinin dolduğu bildirimi oluştur
                existing_notification = request.user.notification_set.filter(
                    notification_type='free_trial_expired'
                ).exists()
                
                if not existing_notification:
                    NotificationService.create_free_trial_expired_notification(
                        user=request.user,
                        profile=profile
                    )
            
            # Abonelik bitmiş kullanıcılar için
            try:
                subscription = request.user.subscription
                if subscription.end_date <= timezone.now():
                    existing_notification = request.user.notification_set.filter(
                        notification_type='expiry',
                        subscription=subscription
                    ).exists()
                    
                    if not existing_notification:
                        NotificationService.create_expiry_notification(
                            user=request.user,
                            subscription=subscription
                        )
            except:
                pass
            
            # Paket satın alma sayfasına yönlendir
            return redirect('paketler')
        
        return None