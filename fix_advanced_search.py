#!/usr/bin/env python3
# Fix advanced search form to allow search with only filters

import re

# Template dosyasını oku
with open('/var/www/judicial_platform/core/templates/core/judicial_decisions.html', 'r') as f:
    content = f.read()

# 1. Form'un normal GET submit yapmasını sağla (AJAX değil)
# advancedSearchForm'u bulup method="GET" ekle
content = re.sub(
    r'<form id="advancedSearchForm" class="search-form"[^>]*>',
    '<form id="advancedSearchForm" class="search-form" method="GET" action=".">',
    content
)

# 2. Arama alanının placeholder'ını güncelle - isteğe bağlı olduğunu belirt
content = re.sub(
    r'(id="advancedSearchInput"[^>]+placeholder=")([^"]+)(")',
    r'\1Arama terimi (isteğe bağlı)\3',
    content
)

# 3. Form submit butonunun type="submit" olduğundan emin ol
content = re.sub(
    r'(<button[^>]+class="btn-search"[^>]*)(>)',
    r'\1 type="submit"\2',
    content
)

# Dosyayı yaz
with open('/var/www/judicial_platform/core/templates/core/judicial_decisions.html', 'w') as f:
    f.write(content)

print("✅ Template dosyası güncellendi")
print("✅ Gelişmiş filtreler artık arama terimi olmadan da çalışabilir")