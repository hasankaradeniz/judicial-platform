import re

# Views.py dosyasını oku
with open('core/views.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Chamber parametresini ekle
content = re.sub(
    r"(court_type = request\.GET\.get\('court_type', ''\)\.strip\(\))",
    r"\1\n    chamber = request.GET.get('chamber', '').strip()",
    content
)

# has_any_filter'a chamber ekle
content = re.sub(
    r"(has_any_filter = any\(\[query, court_type, case_number, decision_number, date_from, date_to\]\))",
    r"has_any_filter = any([query, court_type, chamber, case_number, decision_number, date_from, date_to])",
    content
)

# Chamber filtresini ekle
content = re.sub(
    r"(# Mahkeme türü filtresi\s+if court_type:\s+where_conditions\.append\(\"karar_turu ILIKE %s\"\)\s+params\.append\(f'%{court_type}%'\))",
    r"\1\n            \n            # Daire filtresi\n            if chamber:\n                where_conditions.append(\"karar_veren_mahkeme ILIKE %s\")\n                params.append(f'%{chamber}%')",
    content,
    flags=re.DOTALL
)

# Context'e chamber ekle
content = re.sub(
    r"('court_type': court_type,)",
    r"\1\n        'chamber': chamber,",
    content
)

# Dosyayı yaz
with open('core/views.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ Chamber filtresi basit şekilde eklendi')