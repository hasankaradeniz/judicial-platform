#!/usr/bin/env python
"""
Test link click functionality
"""

import requests

def test_links():
    """Test external mevzuat links"""
    base_url = "http://127.0.0.1:8000"
    
    test_links = [
        "/external-mevzuat/live_4721/",
        "/external-mevzuat/live_5237/", 
        "/external-mevzuat/live_4722/"
    ]
    
    for link in test_links:
        try:
            url = f"{base_url}{link}"
            print(f"Testing: {url}")
            
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                print(f"✅ {link} - OK ({response.status_code})")
                
                # Check if content contains mevzuat
                if 'MADDE' in response.text or 'KANUN' in response.text:
                    print(f"   📄 Content loaded successfully")
                else:
                    print(f"   ⚠️  Content may not be loaded properly")
            else:
                print(f"❌ {link} - Error ({response.status_code})")
                
        except Exception as e:
            print(f"❌ {link} - Exception: {str(e)}")
            
        print("-" * 50)

if __name__ == "__main__":
    test_links()