from django.shortcuts import redirect
from django.utils import timezone

def subscription_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        subscription = getattr(request.user, 'subscription', None)
        if not subscription or subscription.end_date < timezone.now():
            return redirect('subscription_payment')
        return view_func(request, *args, **kwargs)
    return _wrapped_view
