import re

# Views.py dosyasını oku
with open('core/views.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Context'e filter sonuçlarını göstermek için bir flag ekle
content = re.sub(
    r"(context = \{[^}]+)'has_filters': has_any_filter,",
    r"\1'has_filters': has_any_filter,\n        'filter_results': has_any_filter,  # Filtre sonuçları gösterilmeli mi",
    content,
    flags=re.DOTALL
)

# Dosyayı yaz
with open('core/views.py', 'w', encoding='utf-8') as f:
    f.write(content)

# Template dosyasını da düzelt
with open('core/templates/core/judicial_decisions.html', 'r') as f:
    template = f.read()

# En Yeni Kararlar başlığını filtre durumuna göre değiştir
template = re.sub(
    r'<div class="results-count">En Yeni Kararlar</div>',
    '''<div class="results-count">
        {% if has_filters %}
            Arama Sonuçları
        {% else %}
            En Yeni Kararlar
        {% endif %}
    </div>''',
    template
)

# Sonuç sayısını düzelt
template = re.sub(
    r'<div style="color: var\(--gray-600\);">Son eklenen {{ newest_decisions\|length }} karar</div>',
    '''<div style="color: var(--gray-600);">
        {% if has_filters %}
            Toplam {{ total_decisions }} sonuç bulundu, {{ newest_decisions|length }} tanesi gösteriliyor
        {% else %}
            Son eklenen {{ newest_decisions|length }} karar
        {% endif %}
    </div>''',
    template
)

# latestDecisionsContainer'ın görünürlük mantığını düzelt
template = re.sub(
    r'<div id="latestDecisionsContainer" class="container" style="{% if query %}display: none;{% endif %}">',
    '<div id="latestDecisionsContainer" class="container">',
    template
)

# Dosyayı yaz
with open('core/templates/core/judicial_decisions.html', 'w') as f:
    f.write(template)

print('✅ Filtre sonuç gösterimi düzeltildi')
print('✅ Başlık dinamik hale getirildi')
print('✅ Toplam sonuç sayısı gösteriliyor')