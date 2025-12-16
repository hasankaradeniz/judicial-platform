from django.db import connection

cursor = connection.cursor()

# Kategori ile ilgili tablolar
cursor.execute("""
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND (table_name LIKE '%kategori%' OR table_name LIKE '%hukuk%')
ORDER BY table_name;
""")

tables = cursor.fetchall()
print('Kategori ile ilgili tablolar:')
for table in tables:
    print(f'- {table[0]}')

# Tüm tabloları kontrol et
cursor.execute("""
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;
""")

all_tables = cursor.fetchall()
print('\nTüm tablolar:')
for table in all_tables:
    if 'kategori' in table[0] or 'hukuk' in table[0] or 'legal' in table[0]:
        print(f'✓ {table[0]}')
    else:
        print(f'  {table[0]}')
