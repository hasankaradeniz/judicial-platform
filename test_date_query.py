import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'judicial_platform.settings')
import django
django.setup()

from django.db import connection
from datetime import datetime, timedelta

# Test sorgusu
with connection.cursor() as cursor:
    # Son 5 yılın Yargıtay kararlarını say
    date_from = (datetime.now() - timedelta(days=1825)).date().isoformat()
    
    sql = '''
        SELECT COUNT(*), MIN(karar_tarihi), MAX(karar_tarihi)
        FROM core_judicialdecision
        WHERE karar_turu ILIKE %s
        AND karar_tarihi >= %s
    '''
    
    cursor.execute(sql, ['%yargıtay%', date_from])
    result = cursor.fetchone()
    
    print(f'Toplam Yargıtay kararı (son 5 yıl): {result[0]}')
    print(f'En eski tarih: {result[1]}')
    print(f'En yeni tarih: {result[2]}')
    
    # Tüm kararların tarih dağılımı
    cursor.execute('''
        SELECT EXTRACT(YEAR FROM karar_tarihi) as yil, COUNT(*)
        FROM core_judicialdecision
        WHERE karar_tarihi IS NOT NULL
        GROUP BY yil
        ORDER BY yil DESC
        LIMIT 10
    ''')
    
    print('\nYıllara göre karar dağılımı:')
    for row in cursor.fetchall():
        print(f'{int(row[0]) if row[0] else NULL}: {row[1]} karar')
