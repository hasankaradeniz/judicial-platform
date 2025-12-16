# Simple subscription creation

user_username = "Av.Ertuğrul55"

# Import modules
from django.contrib.auth.models import User
from core.models import UserProfile, Subscription
from django.utils import timezone
from datetime import timedelta

# Find user
user = User.objects.get(username=user_username)
profile = UserProfile.objects.get(user=user)

print(f"User found: {user.username}")

# Create or update subscription
try:
    subscription = Subscription.objects.get(user=user)
    print("Updating existing subscription")
except Subscription.DoesNotExist:
    subscription = Subscription(user=user)
    print("Creating new subscription")

# Set 3-month subscription
start_date = timezone.now()
end_date = start_date + timedelta(days=90)

subscription.plan = "quarterly"
subscription.start_date = start_date  
subscription.end_date = end_date
subscription.save()

# Update profile
profile.is_free_trial = False
profile.save()

print(f"Plan: {subscription.get_plan_display()}")
print(f"Start: {subscription.start_date.date()}")
print(f"End: {subscription.end_date.date()}")
print("3-month subscription created successfully\!")
