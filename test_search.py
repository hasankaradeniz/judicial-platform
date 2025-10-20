#\!/usr/bin/env python3

import requests
import json

class TestSearcher:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Academic Research Tool (contact@research.com)',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
    
    def test_crossref(self, query):
        try:
            url = "https://api.crossref.org/works"
            params = {
                'query': query,
                'rows': 5,
                'sort': 'relevance',
                'filter': 'type:journal-article'
            }
            
            response = self.session.get(url, params=params, timeout=10)
            print(f"CrossRef Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                items = data.get('message', {}).get('items', [])
                print(f"CrossRef sonuçları: {len(items)}")
                
                for i, item in enumerate(items[:3]):
                    title = item.get('title', [''])[0] if item.get('title') else ''
                    print(f"  {i+1}. {title[:80]}...")
                
                return len(items)
            else:
                print(f"CrossRef Error: {response.text}")
                return 0
                
        except Exception as e:
            print(f"CrossRef Exception: {e}")
            return 0

if __name__ == "__main__":
    searcher = TestSearcher()
    query = "law"
    
    print(f"=== Testing APIs with query: '{query}' ===")
    crossref_count = searcher.test_crossref(query)
    print(f"Total results: {crossref_count}")
EOF < /dev/null