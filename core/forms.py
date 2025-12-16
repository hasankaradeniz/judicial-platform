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
    
    # Adres bilgileri - fatura için gerekli
    address_line_1 = forms.CharField(
        label="Adres Satırı 1",
        max_length=255,
        required=True,
        help_text="Mahalle, cadde, sokak ve kapı numarası",
        widget=forms.TextInput(attrs={
            'placeholder': 'Örn: Atatürk Mah. İstiklal Cad. No: 123',
            'class': 'form-control'
        })
    )
    address_line_2 = forms.CharField(
        label="Adres Satırı 2",
        max_length=255,
        required=False,
        help_text="Apartman, daire numarası gibi ek bilgiler (opsiyonel)",
        widget=forms.TextInput(attrs={
            'placeholder': 'Örn: A Blok Daire: 45 (opsiyonel)',
            'class': 'form-control'
        })
    )
    city = forms.CharField(
        label="Şehir",
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'Örn: İstanbul',
            'class': 'form-control'
        })
    )
    district = forms.CharField(
        label="İlçe",
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'Örn: Kadıköy',
            'class': 'form-control'
        })
    )
    postal_code = forms.CharField(
        label="Posta Kodu",
        max_length=10,
        required=False,
        validators=[
            RegexValidator(
                r'^\d{5}$', 
                "Geçerli bir posta kodu giriniz. (Örn: 34000)"
            )
        ],
        widget=forms.TextInput(attrs={
            'placeholder': '34000 (opsiyonel)',
            'class': 'form-control',
            'pattern': r'\d{5}',
            'title': 'Geçerli bir posta kodu giriniz (5 haneli sayı)'
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
        fields = ("username", "email", "phone_number", "address_line_1", "address_line_2", "city", "district", "postal_code", "password1", "password2", "accept_user_agreement", "accept_privacy_policy", "accept_data_protection")
    
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
            # Signals çalıştıktan sonra profile bilgilerini güncelle
            from .models import UserProfile
            import time
            
            # Profile'ın signal ile oluşturulmasını bekle
            time.sleep(0.1)  # Kısa bir bekleme
            
            try:
                profile, created = UserProfile.objects.get_or_create(user=user)
                
                # Form verilerini profile'a ata
                profile.phone_number = self.cleaned_data.get("phone_number", "")
                profile.address_line_1 = self.cleaned_data.get("address_line_1", "")
                profile.address_line_2 = self.cleaned_data.get("address_line_2", "")
                profile.city = self.cleaned_data.get("city", "")
                profile.district = self.cleaned_data.get("district", "")
                profile.postal_code = self.cleaned_data.get("postal_code", "")
                profile.save()
                
            except Exception as e:
                print(f"Error saving profile data: {e}")
        return user
