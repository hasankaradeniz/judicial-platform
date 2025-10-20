import re

# Template dosyasını oku
with open('core/templates/core/judicial_decisions.html', 'r') as f:
    content = f.read()

# Filtreli Arama butonunu normal submit butonu yap
content = re.sub(
    r'<button[^>]*class="btn-search"[^>]*>\s*<i[^>]*></i>\s*Filtreli Arama\s*</button>',
    '<button type="submit" class="btn-search"><i class="fas fa-filter"></i> Filtreli Arama</button>',
    content,
    flags=re.DOTALL
)

# performSearch çağrılarını kaldır
content = re.sub(r'onclick="performSearch\([^)]*\)"', '', content)

# Form'un kendisini daha basit hale getir - action boş olsun ki aynı sayfaya gitsin
content = re.sub(
    r'<form id="advancedSearchForm"[^>]*>',
    '<form id="advancedSearchForm" class="search-form" method="GET">',
    content
)

# Dosyayı yaz
with open('core/templates/core/judicial_decisions.html', 'w') as f:
    f.write(content)

print("Form düzeltildi\!")
