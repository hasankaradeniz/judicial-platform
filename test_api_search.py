import requests
import json

def test_search(query, description=""):
    print(f"\n=== {description} ===")
    print(f"Searching for: \"{query}\"")
    
    response = requests.get("https://www.mevzuat.gov.tr/api/search", params={"q": query})
    
    if response.status_code == 200:
        data = response.json()
        total = data.get("total", 0)
        items = data.get("items", [])
        
        print(f"Total results: {total}")
        print(f"Response keys: {list(data.keys())}")
        
        if items:
            for i, item in enumerate(items[:5]):
                print(f"\nResult {i+1}:")
                print(f"  Title: {item.get('title', 'N/A')}")
                print(f"  Type: {item.get('type', 'N/A')}")
                print(f"  Number: {item.get('number', 'N/A')}")
                print(f"  Date: {item.get('date', 'N/A')}")
                print(f"  URL: {item.get('url', 'N/A')}")
                # Show all available fields
                print(f"  All fields: {list(item.keys())}")
        else:
            print("No items found in response")
    else:
        print(f"Error: {response.status_code}")
        print(f"Response: {response.text[:500]}")

# Test different searches
test_search("6769", "TEST 1: Law number 6769 (Sınai Mülkiyet Kanunu)")
test_search("5846", "TEST 2: Law number 5846 (Fikir ve Sanat Eserleri Kanunu)")
test_search("fikir ve sanat", "TEST 3: Search for 'fikir ve sanat'")
test_search("sınai mülkiyet", "TEST 4: Search for 'sınai mülkiyet'")
test_search("patent", "TEST 5: Search for 'patent'")
test_search("marka", "TEST 6: Search for 'marka'")
test_search("fikri", "TEST 7: Original search for 'fikri'")

# Test with different API endpoints if they exist
print("\n\n=== Testing different API endpoints ===")
endpoints = [
    "https://www.mevzuat.gov.tr/api/kanunlar",
    "https://www.mevzuat.gov.tr/api/legislation",
    "https://www.mevzuat.gov.tr/api/laws"
]

for endpoint in endpoints:
    print(f"\nTesting endpoint: {endpoint}")
    try:
        response = requests.get(endpoint, timeout=5)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print(f"Response preview: {response.text[:200]}...")
    except Exception as e:
        print(f"Error: {e}")
