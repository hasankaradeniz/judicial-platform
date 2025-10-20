#!/usr/bin/env python
"""
Sadece Selenium ile arama test et
"""

import os
import sys
import django

# Django setup
sys.path.append('/Users/hasankaradeniz/PycharmProjects/Yargı_Veri_Tabani kopyası/judicial_platform')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'judicial_platform.settings')
django.setup()

from core.simple_mevzuat_search import SimpleMevzuatSearcher
import logging

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_selenium_only():
    """Sadece Selenium ile test"""
    searcher = SimpleMevzuatSearcher()
    
    query = "türk medeni kanunu"
    
    print(f"Selenium ile arama: '{query}'")
    print("="*50)
    
    try:
        # Direkt Selenium'u çağır
        results = searcher._try_selenium_search(query, None, 1, 20)
        
        print(f"Toplam sonuç: {results['total_count']}")
        print(f"Dönen sonuç sayısı: {len(results['results'])}")
        
        if results['results']:
            print("\nBulunan sonuçlar:")
            for i, result in enumerate(results['results'][:10]):  # İlk 10 sonuç
                print(f"{i+1}. {result['title']}")
                print(f"   Tür: {result['type']}")
                print(f"   No: {result['mevzuat_no']}")
                print(f"   URL: {result['external_url']}")
                print(f"   Kaynak: {result['source']}")
                print()
        else:
            print("Hiç sonuç bulunamadı!")
            if 'error' in results:
                print(f"Hata: {results['error']}")
                
    except Exception as e:
        print(f"HATA: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_selenium_only()