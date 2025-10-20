#!/usr/bin/env python
"""
Mevzuat.gov.tr AJAX arama endpoint'ini test et
"""

import requests
from bs4 import BeautifulSoup
import json
import time

def debug_ajax_search():
    """AJAX arama endpoint'ini debug et"""
    query = "medeni kanun"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Referer': 'https://www.mevzuat.gov.tr/aramasonuc',
        'Origin': 'https://www.mevzuat.gov.tr',
        'X-Requested-With': 'XMLHttpRequest'
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
        
        # İlk olarak normal POST arama yap
        post_data = {
            'AranacakMetin': query,
            'antiforgerytoken': antiforgery_token
        }
        
        print(f"POST arama: {query}")
        response = session.post("https://www.mevzuat.gov.tr/aramasonuc", data=post_data, timeout=20)
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            # Şimdi AJAX endpoint'ini dene
            ajax_endpoints = [
                "/GenelArama/GenelAramaList",
                "/api/GeneralSearch",
                "/GeneralSearch/Search",
                "/Search/GeneralSearch",
                "/mevzuat/search"
            ]
            
            for endpoint in ajax_endpoints:
                print(f"\n--- Test ediliyor: {endpoint} ---")
                try:
                    # Farklı AJAX parametre formatları dene
                    ajax_data_formats = [
                        {
                            'searchText': query,
                            'searchType': 'Baslik',
                            'mevzuatTur': '0',
                            'pageIndex': 0
                        },
                        {
                            'text': query,
                            'type': 'Baslik',
                            'tur': 0
                        },
                        {
                            'AranacakMetin': query,
                            'AramaTuru': 'Baslik',
                            'MevzuatTuru': 0
                        }
                    ]
                    
                    for i, ajax_data in enumerate(ajax_data_formats):
                        print(f"  Format {i+1}: {ajax_data}")
                        
                        # POST olarak dene
                        ajax_response = session.post(
                            f"https://www.mevzuat.gov.tr{endpoint}",
                            data=ajax_data,
                            timeout=10
                        )
                        
                        print(f"    POST Status: {ajax_response.status_code}")
                        if ajax_response.status_code == 200:
                            content_type = ajax_response.headers.get('content-type', '')
                            print(f"    Content-Type: {content_type}")
                            
                            if 'json' in content_type.lower():
                                try:
                                    json_data = ajax_response.json()
                                    print(f"    JSON response: {str(json_data)[:200]}...")
                                    
                                    # JSON'da sonuç var mı kontrol et
                                    if isinstance(json_data, dict):
                                        for key in ['data', 'results', 'items', 'list']:
                                            if key in json_data and json_data[key]:
                                                print(f"    ✓ {key} anahtarında {len(json_data[key])} sonuç bulundu!")
                                                return endpoint, ajax_data, json_data
                                except:
                                    print(f"    JSON parse hatası")
                            else:
                                print(f"    HTML response: {ajax_response.text[:200]}...")
                                
                                # HTML'de tablo var mı kontrol et
                                if '<table' in ajax_response.text or '<tr' in ajax_response.text:
                                    print(f"    ✓ HTML'de tablo yapısı bulundu!")
                                    return endpoint, ajax_data, ajax_response.text
                        
                        time.sleep(0.5)  # Rate limiting
                        
                except Exception as e:
                    print(f"    Hata: {str(e)}")
                    continue
    
    print("\nHiçbir AJAX endpoint'i çalışmadı")
    return None, None, None

if __name__ == "__main__":
    endpoint, data, response = debug_ajax_search()
    if endpoint:
        print(f"\n🎉 BAŞARILI ENDPOINT: {endpoint}")
        print(f"📊 Kullanılan data: {data}")
        print(f"📋 Response türü: {type(response)}")