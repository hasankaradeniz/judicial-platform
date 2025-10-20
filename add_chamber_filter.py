import re

# Views.py dosyasını oku
with open('core/views.py', 'r', encoding='utf-8') as f:
    content = f.read()

# chamber parametresini ekle (court_type'dan sonra)
content = re.sub(
    r"(court_type = request\.GET\.get\('court_type', ''\)\.strip\(\))",
    r"\1\n    chamber = request.GET.get('chamber', '').strip()",
    content
)

# has_any_filter'a chamber'ı ekle
content = re.sub(
    r"(has_any_filter = any\(\[query, court_type, case_number, decision_number, date_from, date_to\]\))",
    r"has_any_filter = any([query, court_type, chamber, case_number, decision_number, date_from, date_to])",
    content
)

# Chamber filtresi için WHERE koşulu ekle (court_type'dan sonra)
chamber_filter = '''
            # Daire filtresi
            if chamber:
                where_conditions.append("karar_veren_mahkeme ILIKE %s")
                params.append(f'%{chamber}%')
'''

# Court type filtresinden sonra ekle
pattern = r"(# Mahkeme türü filtresi.*?params\.append\(f'%\{court_type\}%'\))"
replacement = r"\1\n" + chamber_filter

content = re.sub(pattern, replacement, content, flags=re.DOTALL)

# Context'e chamber ekle
content = re.sub(
    r"('court_type': court_type,)",
    r"\1\n        'chamber': chamber,",
    content
)

# Dosyayı yaz
with open('core/views.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ Chamber filtresi eklendi!')
print('✅ Artık Daire ile de filtreleme yapılabilir')