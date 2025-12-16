from django.db import connection

cursor = connection.cursor()

print('=== ÖRNEK HUKUK KATEGORILERI (İlk 15) ===')
cursor.execute('SELECT kod, ana_kategori, ana_alan, alt_alan, detay_alan FROM hukuk_kategorileri WHERE kod IS NOT NULL ORDER BY kod LIMIT 15;')
categories = cursor.fetchall()
for cat in categories:
    hierarchy = ' > '.join(filter(None, [cat[1], cat[2], cat[3], cat[4]]))
    print(f'  {cat[0]}: {hierarchy}')

print('\n=== KARAR KATEGORI İLIŞKI SAYILARI ===')
cursor.execute('SELECT COUNT(*) FROM karar_kategori_iliskileri;')
count = cursor.fetchone()[0]
print(f'  Toplam ilişki: {count:,}')

print('\n=== EN POPÜLER KATEGORILER ===')
cursor.execute("""
SELECT hk.kod, hk.ana_kategori, hk.ana_alan, hk.alt_alan, COUNT(kki.id) as karar_sayisi
FROM hukuk_kategorileri hk
LEFT JOIN karar_kategori_iliskileri kki ON hk.id = kki.kategori_id
WHERE hk.kod IS NOT NULL
GROUP BY hk.id, hk.kod, hk.ana_kategori, hk.ana_alan, hk.alt_alan
ORDER BY karar_sayisi DESC
LIMIT 10;
""")

top_categories = cursor.fetchall()
for cat in top_categories:
    hierarchy = ' > '.join(filter(None, [cat[1], cat[2], cat[3]]))
    print(f'  {cat[0]}: {hierarchy} ({cat[4]:,} karar)')

print('\n=== BİR KARARIN KATEGORİLERİ (Örnek) ===')
cursor.execute("""
SELECT hk.kod, hk.ana_kategori, hk.ana_alan, hk.alt_alan, hk.detay_alan
FROM karar_kategori_iliskileri kki
JOIN hukuk_kategorileri hk ON kki.kategori_id = hk.id
WHERE kki.karar_id = (SELECT karar_id FROM karar_kategori_iliskileri LIMIT 1)
ORDER BY hk.kod;
""")

example_categories = cursor.fetchall()
if example_categories:
    print(f'  Karar ID: {example_categories[0]} kategorileri:')
    for cat in example_categories:
        hierarchy = ' > '.join(filter(None, [cat[1], cat[2], cat[3], cat[4]]))
        print(f'    {cat[0]}: {hierarchy}')
