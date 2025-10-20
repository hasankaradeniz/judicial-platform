import re
from datetime import datetime, timedelta

# Views.py dosyasını oku
with open('core/views.py', 'r', encoding='utf-8') as f:
    content = f.read()

# date_range parametresini ekle
content = re.sub(
    r"(date_from = request\.GET\.get\('date_from', ''\)\.strip\(\))",
    r"date_range = request.GET.get('date_range', '').strip()\n    \1",
    content
)

# start_date ve end_date parametrelerini ekle
content = re.sub(
    r"(date_to = request\.GET\.get\('date_to', ''\)\.strip\(\))",
    r"\1\n    start_date = request.GET.get('start_date', '').strip()\n    end_date = request.GET.get('end_date', '').strip()",
    content
)

# Date range işleme mantığı ekle
date_range_logic = '''
            # Date range seçeneğine göre tarihleri ayarla
            if date_range and not (date_from or date_to):
                today = datetime.now().date()
                if date_range == 'last_6_months':
                    date_from = (today - timedelta(days=180)).isoformat()
                elif date_range == 'last_year':
                    date_from = (today - timedelta(days=365)).isoformat()
                elif date_range == 'last_2_years':
                    date_from = (today - timedelta(days=730)).isoformat()
                elif date_range == 'last_3_years':
                    date_from = (today - timedelta(days=1095)).isoformat()
                elif date_range == 'last_5_years':
                    date_from = (today - timedelta(days=1825)).isoformat()
                elif date_range == '2020_onwards':
                    date_from = '2020-01-01'
                elif date_range == '2015_onwards':
                    date_from = '2015-01-01'
                elif date_range == '2010_onwards':
                    date_from = '2010-01-01'
            
            # Özel tarih aralığı (start_date ve end_date)
            if start_date:
                date_from = start_date
            if end_date:
                date_to = end_date
'''

# Tarih filtrelerinden önce ekle
content = re.sub(
    r"(# Tarih aralığı filtreleri)",
    date_range_logic + "\n            \\1",
    content
)

# has_any_filter'a yeni parametreleri ekle
content = re.sub(
    r"(has_any_filter = any\(\[query, court_type, chamber, case_number, decision_number, date_from, date_to\]\))",
    r"has_any_filter = any([query, court_type, chamber, case_number, decision_number, date_from, date_to, date_range, start_date, end_date])",
    content
)

# Context'e yeni parametreleri ekle
content = re.sub(
    r"('date_to': date_to,)",
    r"\\1\n        'date_range': date_range,\n        'start_date': start_date,\n        'end_date': end_date,",
    content
)

# datetime import'u ekle
if "from datetime import" not in content:
    content = re.sub(
        r"(from django\.db import connection)",
        r"from datetime import datetime, timedelta\n\\1",
        content
    )

# Dosyayı yaz
with open('core/views.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ Tarih filtreleri düzeltildi!')
print('✅ date_range seçenekleri eklendi')
print('✅ Özel tarih aralığı (start_date, end_date) eklendi')