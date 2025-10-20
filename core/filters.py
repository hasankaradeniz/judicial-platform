# core/filters.py
import django_filters
from django import forms
from .models import JudicialDecision

class JudicialDecisionFilter(django_filters.FilterSet):
    karar_tam_metni = django_filters.CharFilter(
        lookup_expr='icontains',
        label="Kararın Tam Metni",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Kararın tam metni içinde ara...'})
    )

    anahtar_kelimeler = django_filters.CharFilter(
        lookup_expr='icontains',
        label="Anahtar Kelimeler",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Anahtar kelime girin...'})
    )

    karar_turu = django_filters.CharFilter(
        lookup_expr='icontains',
        label="Karar Türü (Mahkeme)",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Örneğin: Yargıtay'})
    )
    # Kararı veren mahkeme; choices dinamik olarak ayarlanacak
    karar_veren_mahkeme = django_filters.ChoiceFilter(
        lookup_expr='icontains',
        label="Kararı Veren Mahkeme",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    karar_ozeti = django_filters.CharFilter(
        lookup_expr='icontains',
        label="Kararın Özeti",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Özet içinde ara...'})
    )

    class Meta:
        model = JudicialDecision
        fields = ['karar_tam_metni', 'anahtar_kelimeler','karar_turu', 'karar_veren_mahkeme', 'karar_ozeti', ]

    def __init__(self, *args, **kwargs):
        super(JudicialDecisionFilter, self).__init__(*args, **kwargs)
        # Eğer karar_turu alanında bir değer varsa, dinamik olarak karar_veren_mahkeme seçeneklerini ayarla.
        karar_turu_val = self.data.get('karar_turu', '')
        self.filters['karar_veren_mahkeme'].extra['choices'] = self.get_court_choices(karar_turu_val)

    def get_court_choices(self, karar_turu_value=None):
        if karar_turu_value:
            qs = JudicialDecision.objects.filter(karar_turu__icontains=karar_turu_value)
        else:
            qs = JudicialDecision.objects.all()
        choices = qs.values_list('karar_veren_mahkeme', flat=True).distinct()
        return [('', 'Tümü')] + [(c, c) for c in choices if c]
