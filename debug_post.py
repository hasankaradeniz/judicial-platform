#!/usr/bin/env python
"""
POST arama sonuç sayfasını debug et
"""

import requests
from bs4 import BeautifulSoup

def debug_post_search():
    """POST arama sonuç sayfasını debug et"""
    query = "medeni kanun"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Referer': 'https://www.mevzuat.gov.tr/',
        'Origin': 'https://www.mevzuat.gov.tr'
    }
    
    # Session oluştur
    session = requests.Session()
    session.headers.update(headers)
    
    print("Ana sayfa ziyaret ediliyor...")
    main_page = session.get("https://www.mevzuat.gov.tr/", timeout=15)
    
    if main_page.status_code == 200:
        # Anti-forgery token bul
        soup = BeautifulSoup(main_page.content, 'html.parser')
        antiforgery_input = soup.find('input', {'name': 'antiforgerytoken'})
        antiforgery_token = antiforgery_input.get('value', '') if antiforgery_input else ''
        
        print(f"Token: {antiforgery_token[:30]}...")
        
        # POST verisi
        post_data = {
            'AranacakMetin': query,
            'antiforgerytoken': antiforgery_token
        }
        
        print(f"POST arama: {query}")
        response = session.post("https://www.mevzuat.gov.tr/aramasonuc", data=post_data, timeout=20)
        
        print(f"Response status: {response.status_code}")
        print(f"Response URL: {response.url}")
        
        if response.status_code == 200:
            # HTML'i dosyaya kaydet
            with open('/tmp/post_search_result.html', 'w', encoding='utf-8') as f:
                f.write(response.text)
            print("HTML saved to /tmp/post_search_result.html")
            
            # Sonuçları parse et
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Sayfa başlığı
            title = soup.find('title')
            print(f"Sayfa başlığı: {title.get_text() if title else 'Yok'}")
            
            # Arama sonucu metinleri
            print("\nARAMA SONUCU METİNLERİ:")
            result_indicators = ['sonuç', 'bulunan', 'adet', 'toplam', 'kayıt']
            for keyword in result_indicators:
                elements = soup.find_all(string=lambda text: text and keyword.lower() in text.lower())
                for elem in elements[:3]:
                    print(f"  '{keyword}': {str(elem).strip()[:100]}")
            
            # Tablolarda ara
            print(f"\nTABLOLAR: {len(soup.find_all('table'))}")
            tables = soup.find_all('table')
            for i, table in enumerate(tables):
                print(f"Tablo {i+1}:")
                rows = table.find_all('tr')
                print(f"  {len(rows)} satır")
                for j, row in enumerate(rows[:5]):  # İlk 5 satır
                    cells = row.find_all(['td', 'th'])
                    if cells:
                        cell_texts = [cell.get_text(strip=True)[:30] for cell in cells[:3]]
                        print(f"    Satır {j+1}: {' | '.join(cell_texts)}")
            
            # Div'lerde mevzuat ara
            print("\nMEVZUAT DIV'LERİ:")
            mevzuat_divs = soup.find_all('div', string=lambda text: text and any(
                keyword in text.lower() for keyword in ['kanun', 'yönetmelik', 'tüzük']
            ))
            for i, div in enumerate(mevzuat_divs[:5]):
                print(f"  Div {i+1}: {div.get_text(strip=True)[:100]}")
            
            # Script içeriği kontrol et
            print("\nSCRIPT İÇERİKLERİ:")
            scripts = soup.find_all('script')
            for i, script in enumerate(scripts):
                if script.string and ('mevzuat' in script.string.lower() or 'sonuc' in script.string.lower()):
                    print(f"  Script {i+1}: {script.string[:200]}...")
            
            # HTML snippet
            print(f"\nHTML SNIPPET (ilk 1000 karakter):")
            print(response.text[:1000])
            print("...")
            
    else:
        print(f"Ana sayfa hatası: {main_page.status_code}")

if __name__ == "__main__":
    debug_post_search()