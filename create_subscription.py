from django.contrib.auth.models import User
from core.models import UserProfile, Subscription
from django.utils import timezone
from datetime import timedelta
import os
import django

# Django setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "judicial_platform.settings")
django.setup()

# Kullanıcıyı bul
user = User.objects.get(username="Av.Ertuğrul55")
profile = UserProfile.objects.get(user=user)

print("=== 3 AYLIK ABONELİK OLUŞTURULUYOR ===")
print(f"Kullanıcı: {user.username}")

# Mevcut abonelik kontrolü
try:
    subscription = Subscription.objects.get(user=user)
    print("Mevcut abonelik bulundu, güncelleniyor...")
except Subscription.DoesNotExist:
    subscription = Subscription(user=user)
    print("Yeni abonelik oluşturuluyor...")

# 3 aylık abonelik ayarları
start_date = timezone.now()
end_date = start_date + timedelta(days=90)  # 3 ay = 90 gün

subscription.plan = "quarterly"
subscription.start_date = start_date  
subscription.end_date = end_date
subscription.save()

# Profili güncelle
profile.is_free_trial = False
profile.save()

print("\n=== ABONELİK BİLGİLERİ ===")
print(f"Plan: {subscription.get_plan_display()}")
print(f"Başlangıç: {subscription.start_date.date()}")
print(f"Bitiş: {subscription.end_date.date()}")
print("Süre: 90 gün (3 ay)")

print("\n✅ 3 aylık abonelik başarıyla tanımlandı\!")
print("✅ Kullanıcı artık tam aboneli\!")
