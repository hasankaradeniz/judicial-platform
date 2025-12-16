from .models import UserProfile

def trial_status(request):
    """
    Template'lerde kullanılmak üzere deneme durumu bilgilerini ekler
    """
    context = {
        'trial_info': {
            'is_trial': False,
            'is_expired': False,
            'remaining_days': 0,
            'ending_soon': False,
            'has_subscription': False,
            'can_access': True,
        }
    }
    
    if request.user.is_authenticated:
        try:
            profile = request.user.profile
            context['trial_info'] = {
                'is_trial': profile.is_free_trial,
                'is_expired': profile.is_free_trial_expired(),
                'remaining_days': profile.get_remaining_trial_days(),
                'ending_soon': profile.is_trial_ending_soon(),
                'has_subscription': profile.has_active_subscription(),
                'can_access': profile.can_access_platform(),
            }
        except UserProfile.DoesNotExist:
            pass
    
    return context