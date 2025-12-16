from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.validators import RegexValidator

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(
        label="E-Posta", 
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    phone_number = forms.CharField(
        label="Telefon Numarası",
        max_length=15,
        required=True,
        validators=[
            RegexValidator(
                r'^[\+\d\s\-\(\)]+$', 
                "Geçerli bir telefon numarası giriniz. (Örn: 05551234567 veya +90 555 123 45 67)"
            )
        ],
        help_text="Telefon numaranızı giriniz",
        widget=forms.TextInput(attrs={
            'placeholder': '05551234567',
            'class': 'form-control',
            'pattern': r'[\+\d\s\-\(\)]+',
            'title': 'Geçerli bir telefon numarası giriniz (Örn: 05551234567)'
        })
    )
    accept_user_agreement = forms.BooleanField(
        label="Kullanıcı Sözleşmesi'ni kabul ediyorum.",
        required=True
    )
    accept_privacy_policy = forms.BooleanField(
        label="Gizlilik Politikası'nı kabul ediyorum.",
        required=True
    )
    accept_data_protection = forms.BooleanField(
        label="Kişisel Verileri Koruma Aydınlatma Metni'ni kabul ediyorum.",
        required=True
    )

    class Meta:
        model = User
        fields = ("username", "email", "phone_number", "password1", "password2", "accept_user_agreement", "accept_privacy_policy", "accept_data_protection")
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Tüm form alanlarına form-control class'ı ekle (checkbox'lar hariç)
        for field_name, field in self.fields.items():
            if field_name not in ['accept_user_agreement', 'accept_privacy_policy', 'accept_data_protection']:
                # Mevcut class'ları koru ve form-control ekle
                existing_classes = field.widget.attrs.get('class', '')
                if 'form-control' not in existing_classes:
                    field.widget.attrs['class'] = f"{existing_classes} form-control".strip()

    def clean(self):
        cleaned_data = super().clean()
        # Kullanıcının tüm kutucukları işaretlediğini doğrulayalım
        if not cleaned_data.get("accept_user_agreement"):
            self.add_error("accept_user_agreement", "Kullanıcı Sözleşmesi kabul edilmelidir.")
        if not cleaned_data.get("accept_privacy_policy"):
            self.add_error("accept_privacy_policy", "Gizlilik Politikası kabul edilmelidir.")
        if not cleaned_data.get("accept_data_protection"):
            self.add_error("accept_data_protection", "Kişisel Verileri Koruma Aydınlatma Metni kabul edilmelidir.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
            # UserProfile otomatik olarak post_save signal ile oluşturulacak
            # Telefon numarasını profile ekle
            from .models import UserProfile
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.phone_number = self.cleaned_data["phone_number"]
            profile.save()
        return user
