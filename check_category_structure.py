from django.db import connection

cursor = connection.cursor()

print('=== HUKUK_KATEGORILERI TABLOSU ===')
cursor.execute("""
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'hukuk_kategorileri' 
ORDER BY ordinal_position;
""")

columns = cursor.fetchall()
for col in columns:
    print(f'  {col[0]}: {col[1]} (NULL: {col[2]})')

print('\n=== KARAR_KATEGORI_ILISKILERI TABLOSU ===')
cursor.execute("""
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'karar_kategori_iliskileri' 
ORDER BY ordinal_position;
""")

columns = cursor.fetchall()
for col in columns:
    print(f'  {col[0]}: {col[1]} (NULL: {col[2]})')

print('\n=== ÖRNEK HUKUK KATEGORILERI (İlk 10) ===')
cursor.execute('SELECT kod, ad, ust_kategori_kod FROM hukuk_kategorileri ORDER BY kod LIMIT 10;')
categories = cursor.fetchall()
for cat in categories:
    print(f'  {cat[0]}: {cat[1]} (Üst: {cat[2]})')

print('\n=== KARAR KATEGORI İLIŞKI SAYILARI ===')
cursor.execute('SELECT COUNT(*) FROM karar_kategori_iliskileri;')
count = cursor.fetchone()[0]
print(f'  Toplam ilişki: {count:,}')

cursor.execute('SELECT kategori_kodu, COUNT(*) as sayi FROM karar_kategori_iliskileri GROUP BY kategori_kodu ORDER BY sayi DESC LIMIT 10;')
top_categories = cursor.fetchall()
print('\n  En popüler kategoriler:')
for cat in top_categories:
    print(f'    {cat[0]}: {cat[1]:,} karar')
