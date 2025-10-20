# Views.py'ye chamber filtresini ekle
with open('core/views.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Chamber parametresini al
content = content.replace(
    "court_type = request.GET.get('court_type', '').strip()",
    """court_type = request.GET.get('court_type', '').strip()
    chamber = request.GET.get('chamber', '').strip()"""
)

# 2. has_any_filter'a ekle  
content = content.replace(
    "has_any_filter = any([query, court_type, case_number, decision_number, date_from, date_to])",
    "has_any_filter = any([query, court_type, chamber, case_number, decision_number, date_from, date_to])"
)

# 3. Chamber WHERE koşulunu ekle
chamber_condition = '''
            # Daire filtresi
            if chamber:
                where_conditions.append("karar_veren_mahkeme ILIKE %s")
                params.append(f'%{chamber}%')
'''

# Court type filtresinden sonra ekle
content = content.replace(
    """            # Mahkeme türü filtresi
            if court_type:
                where_conditions.append("karar_turu ILIKE %s")
                params.append(f'%{court_type}%')""",
    """            # Mahkeme türü filtresi
            if court_type:
                where_conditions.append("karar_turu ILIKE %s")
                params.append(f'%{court_type}%')
""" + chamber_condition
)

# 4. Context'e ekle
content = content.replace(
    "'court_type': court_type,",
    """'court_type': court_type,
        'chamber': chamber,"""
)

with open('core/views.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Chamber filtresi eklendi')
