from django.shortcuts import redirect, render
from django.urls import reverse
from django.contrib import messages
from django.utils import timezone
from .models import UserProfile

class TrialMiddleware:
    """
    Ücretsiz deneme süresi kontrolü middleware'i
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        # Erişime izin verilen URL'ler - URL'leri runtime'da kontrol edelim
        self.allowed_url_patterns = [
            '/signup/',
            '/register/',
            '/login/',
            '/logout/',
            '/',
            '/about/',
            '/paketler/',
            '/gizlilik-politikasi/',
            '/kullanici-sozlesmesi/',
            '/mesafeli-satis-sozlesmesi/',
            '/teslimat-iade-sartlari/',
        ]
        
        # Admin ve static dosyalar için izin
        self.allowed_patterns = [
            '/admin/',
            '/static/',
            '/media/',
            '/payment/',  # Ödeme sayfaları
            '/subscription/',  # Abonelik sayfaları
        ]

    def __call__(self, request):
        # Kullanıcı giriş yapmamışsa middleware'i atla
        if not request.user.is_authenticated:
            return self.get_response(request)
        
        # Superuser ise kontrol etme
        if request.user.is_superuser:
            return self.get_response(request)
        
        # İzin verilen URL'lerde kontrol etme
        current_path = request.path
        if (current_path in self.allowed_url_patterns or 
            any(current_path.startswith(pattern) for pattern in self.allowed_patterns)):
            return self.get_response(request)
        
        try:
            profile = request.user.profile
        except UserProfile.DoesNotExist:
            # Profil yoksa oluştur
            profile = UserProfile.objects.create(user=request.user)
        
        # Aboneliği varsa devam et
        if profile.has_active_subscription():
            return self.get_response(request)
        
        # Ücretsiz deneme süresi kontrolü
        if profile.is_free_trial:
            if profile.is_free_trial_expired():
                # Deneme süresi doldu - abonelik sayfasına yönlendir
                messages.error(request, 
                    'Ücretsiz deneme süreniz sona erdi. Sistemimizi kullanmaya devam etmek için lütfen bir paket seçin.')
                return redirect('paketler')
            
            elif profile.is_trial_ending_soon():
                # Deneme süresi bitmek üzere - uyarı mesajı
                remaining_days = profile.get_remaining_trial_days()
                messages.warning(request, 
                    f'Ücretsiz deneme süreniz {remaining_days} gün sonra sona erecek. '
                    f'Kesintisiz hizmet için bir paket seçmeyi unutmayın.')
        
        # Normal işleme devam et
        return self.get_response(request)

class TrialStatusMiddleware:
    """
    Deneme durumu bilgisini template context'e ekler
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Request'e trial bilgilerini ekle
        if request.user.is_authenticated and hasattr(request.user, 'profile'):
            profile = request.user.profile
            request.trial_info = {
                'is_trial': profile.is_free_trial,
                'is_expired': profile.is_free_trial_expired(),
                'remaining_days': profile.get_remaining_trial_days(),
                'ending_soon': profile.is_trial_ending_soon(),
                'has_subscription': profile.has_active_subscription(),
            }
        else:
            request.trial_info = {
                'is_trial': False,
                'is_expired': False,
                'remaining_days': 0,
                'ending_soon': False,
                'has_subscription': False,
            }
        
        response = self.get_response(request)
        return response