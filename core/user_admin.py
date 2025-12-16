# UserProfile Admin Configuration
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from .models import UserProfile

# Inline for UserProfile
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profil Bilgileri'
    fields = ['phone_number', 'is_free_trial', 'free_trial_start', 'free_trial_end']
    readonly_fields = ['created_at', 'updated_at']

# Custom User Admin
class CustomUserAdmin(UserAdmin):
    inlines = (UserProfileInline,)
    list_display = ['username', 'email', 'get_phone', 'first_name', 'last_name', 'is_active', 'date_joined']
    list_filter = ['is_active', 'is_staff', 'date_joined']
    search_fields = ['username', 'email', 'first_name', 'last_name', 'profile__phone_number']
    
    def get_phone(self, obj):
        try:
            return obj.profile.phone_number or '-'
        except:
            return '-'
    get_phone.short_description = 'Telefon'

# UserProfile Admin
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone_number', 'is_free_trial', 'created_at']
    list_filter = ['is_free_trial', 'created_at']
    search_fields = ['user__username', 'user__email', 'phone_number']
    readonly_fields = ['created_at', 'updated_at']

# Re-register User admin
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
