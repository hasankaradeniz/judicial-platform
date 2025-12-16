"""
Guest user search limit utilities
"""
import hashlib
from datetime import date
from .models import GuestSearchLimit

def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip

def get_user_agent_hash(request):
    """Get hashed user agent string for better privacy"""
    user_agent = request.META.get("HTTP_USER_AGENT", "")
    return hashlib.sha256(user_agent.encode()).hexdigest()

def check_guest_search_limit(request, limit=3):
    """
    Check if guest user has exceeded search limit
    Returns tuple (is_limit_reached, current_count, remaining_searches)
    """
    # If user is authenticated, no limit applies
    if request.user.is_authenticated:
        return False, 0, float("inf")
    
    ip_address = get_client_ip(request)
    user_agent_hash = get_user_agent_hash(request)
    
    try:
        guest_limit, created = GuestSearchLimit.objects.get_or_create(
            ip_address=ip_address,
            user_agent_hash=user_agent_hash,
            date_created=date.today(),
            defaults={"search_count": 0}
        )
        
        # If this is a new day, reset the counter
        if guest_limit.date_created != date.today():
            guest_limit.search_count = 0
            guest_limit.date_created = date.today()
            guest_limit.save()
        
        current_count = guest_limit.search_count
        is_limit_reached = current_count >= limit
        remaining_searches = max(0, limit - current_count)
        
        return is_limit_reached, current_count, remaining_searches
        
    except Exception as e:
        # In case of any error, allow the search
        print(f"Guest limit check error: {e}")
        return False, 0, limit

def increment_guest_search(request):
    """Increment the search count for guest user"""
    if request.user.is_authenticated:
        return True
        
    ip_address = get_client_ip(request)
    user_agent_hash = get_user_agent_hash(request)
    
    try:
        guest_limit, created = GuestSearchLimit.objects.get_or_create(
            ip_address=ip_address,
            user_agent_hash=user_agent_hash,
            date_created=date.today(),
            defaults={"search_count": 0}
        )
        
        # If this is a new day, reset the counter
        if guest_limit.date_created != date.today():
            guest_limit.search_count = 0
            guest_limit.date_created = date.today()
        
        guest_limit.search_count += 1
        guest_limit.save()
        return True
        
    except Exception as e:
        print(f"Guest search increment error: {e}")
        return False

def get_guest_limit_context(request, limit=3):
    """Get context data for templates about guest limits"""
    is_limit_reached, current_count, remaining_searches = check_guest_search_limit(request, limit)
    
    return {
        "is_guest": not request.user.is_authenticated,
        "guest_limit_reached": is_limit_reached,
        "guest_search_count": current_count,
        "guest_remaining_searches": remaining_searches,
        "guest_search_limit": limit,
    }
