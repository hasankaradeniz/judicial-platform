#!/usr/bin/env python
"""
Mevzuat.gov.tr HTML yapısını debug etmek için
"""

import requests
import urllib.parse
from bs4 import BeautifulSoup

def debug_html():
    """HTML yapısını debug et"""
    query = "medeni kanun"
    encoded_query = urllib.parse.quote(query)
    url = f"https://www.mevzuat.gov.tr/mevzuat?Criteria.SearchText={encoded_query}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    print(f"URL: {url}")
    print("="*60)
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # HTML'i dosyaya kaydet
            with open('/tmp/mevzuat_debug.html', 'w', encoding='utf-8') as f:
                f.write(response.text)
            print("HTML saved to /tmp/mevzuat_debug.html")
            
            # Tüm linkleri listele
            print("\nTÜM LİNKLER:")
            print("-" * 40)
            links = soup.find_all('a', href=True)
            for i, link in enumerate(links[:20]):  # İlk 20 link
                href = link.get('href', '')
                text = link.get_text(strip=True)
                print(f"{i+1:2d}. {text[:50]:<50} -> {href}")
            
            # Tablolara bak
            print(f"\nTABLOLAR: {len(soup.find_all('table'))}")
            tables = soup.find_all('table')
            for i, table in enumerate(tables):
                print(f"Tablo {i+1}: {len(table.find_all('tr'))} satır")
                rows = table.find_all('tr')[:3]  # İlk 3 satır
                for j, row in enumerate(rows):
                    cells = row.find_all(['td', 'th'])
                    if cells:
                        print(f"  Satır {j+1}: {len(cells)} hücre")
                        for k, cell in enumerate(cells[:2]):  # İlk 2 hücre
                            print(f"    Hücre {k+1}: {cell.get_text(strip=True)[:30]}")
            
            # Form elementlerine bak
            print(f"\nFORMLAR: {len(soup.find_all('form'))}")
            forms = soup.find_all('form')
            for i, form in enumerate(forms):
                action = form.get('action', '')
                method = form.get('method', '')
                print(f"Form {i+1}: action='{action}' method='{method}'")
                inputs = form.find_all('input')
                for j, inp in enumerate(inputs[:5]):  # İlk 5 input
                    name = inp.get('name', '')
                    type_attr = inp.get('type', '')
                    value = inp.get('value', '')
                    print(f"  Input {j+1}: name='{name}' type='{type_attr}' value='{value}'")
            
            # Sayfa başlığı
            title = soup.find('title')
            print(f"\nSAYFA BAŞLIĞI: {title.get_text() if title else 'Bulunamadı'}")
            
            # Arama sonucu göstergelerini ara
            print("\nARAMA SONUCU GÖSTERGELERİ:")
            keywords = ['sonuç', 'bulunan', 'adet', 'toplam', 'result']
            for keyword in keywords:
                elements = soup.find_all(string=lambda text: text and keyword.lower() in text.lower())
                for elem in elements[:3]:
                    print(f"  '{keyword}': {str(elem).strip()[:100]}")
            
        else:
            print(f"HTTP Error: {response.status_code}")
            
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    debug_html()