import requests
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin, parse_qs, urlparse
import json

class FixedMevzuatService:
    """Düzeltilmiş mevzuat.gov.tr servisi"""
    
    BASE_URL = "https://www.mevzuat.gov.tr"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'tr-TR,tr;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        })
    
    def get_token_and_cookies(self):
        """Ana sayfadan token ve cookie'leri al"""
        try:
            response = self.session.get(self.BASE_URL)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Token'ı bul
            token_input = soup.find('input', {'name': 'antiforgerytoken'})
            token = token_input.get('value') if token_input else None
            
            # AJAX URL'ini bul (DataTables için)
            ajax_pattern = r'ajax.*?url.*?["\']([^"\']+)["\']'
            ajax_match = re.search(ajax_pattern, response.text, re.IGNORECASE)
            ajax_url = ajax_match.group(1) if ajax_match else '/aramasonuc'
            
            return token, ajax_url
            
        except Exception as e:
            print(f"Token alma hatası: {e}")
            return None, '/aramasonuc'
    
    def search_legislation(self, query, page=1):
        """Mevzuat arama"""
        try:
            token, ajax_url = self.get_token_and_cookies()
            
            # Farklı endpoint'ler dene
            endpoints_to_try = [
                '/aramasonuc',  # POST endpoint
                '/Search/SearchResult',  # Alternatif endpoint
                ajax_url  # Dinamik bulunan endpoint
            ]
            
            for endpoint in endpoints_to_try:
                print(f"Trying endpoint: {endpoint}")
                
                # Farklı data formatları dene
                data_formats = [
                    # DataTables format
                    {
                        'draw': page,
                        'start': (page - 1) * 10,
                        'length': 10,
                        'search[value]': query,
                        'search[regex]': 'false',
                        'columns[0][data]': '0',
                        'columns[0][searchable]': 'true',
                        'columns[1][data]': '1',
                        'columns[1][searchable]': 'true',
                        'order[0][column]': '0',
                        'order[0][dir]': 'asc'
                    },
                    # Form format
                    {
                        'AranacakMetin': query,
                        'draw': page,
                        'start': (page - 1) * 10,
                        'length': 10
                    },
                    # Basit format
                    {
                        'q': query,
                        'page': page
                    }
                ]
                
                if token:
                    for data in data_formats:
                        data['antiforgerytoken'] = token
                
                for data in data_formats:
                    response = self.session.post(
                        urljoin(self.BASE_URL, endpoint),
                        data=data,
                        headers={'X-Requested-With': 'XMLHttpRequest'}  # AJAX header
                    )
                    
                    print(f"Response status: {response.status_code}, Length: {len(response.content)}")
                    
                    if response.status_code == 200:
                        # JSON response mı kontrol et
                        try:
                            json_data = response.json()
                            if 'data' in json_data and json_data['data']:
                                return self.parse_json_results(json_data, page)
                        except:
                            pass
                        
                        # HTML response parse et
                        results = self.parse_html_results(response.content, page)
                        if results['results']:
                            return results
            
            # Hiçbiri çalışmazsa boş sonuç döndür
            return {
                'results': [],
                'total_count': 0,
                'has_next': False,
                'has_previous': False,
                'current_page': page,
                'total_pages': 1,
                'error': None
            }
                    
        except Exception as e:
            return {
                'results': [],
                'total_count': 0,
                'has_next': False,
                'has_previous': False,
                'current_page': page,
                'total_pages': 1,
                'error': str(e)
            }
    
    def parse_json_results(self, json_data, page):
        """JSON sonuçlarını parse et"""
        try:
            results = []
            data = json_data.get('data', [])
            
            for row in data:
                if isinstance(row, list) and len(row) >= 2:
                    # DataTables format: [mevzuat_no, title_html, ...]
                    mevzuat_no = str(row[0]) if row[0] else ""
                    title_html = str(row[1]) if row[1] else ""
                    
                    # HTML'den title ve link çıkar
                    soup = BeautifulSoup(title_html, 'html.parser')
                    link = soup.find('a')
                    
                    if link:
                        title = link.get_text(strip=True)
                        detail_url = link.get('href', '')
                        params = self.parse_mevzuat_url(detail_url)
                        
                        result = {
                            'mevzuat_no': mevzuat_no,
                            'title': title,
                            'detail_url': urljoin(self.BASE_URL, detail_url),
                            'pdf_url': self.generate_pdf_url(params),
                            'mevzuat_tur': params.get('MevzuatTur'),
                            'mevzuat_tertip': params.get('MevzuatTertip'),
                            'type': 'Mevzuat'
                        }
                        results.append(result)
            
            total_count = json_data.get('recordsTotal', len(results))
            
            return {
                'results': results,
                'total_count': total_count,
                'has_next': (page * 10) < total_count,
                'has_previous': page > 1,
                'current_page': page,
                'total_pages': (total_count + 9) // 10,
                'error': None
            }
            
        except Exception as e:
            print(f"JSON parse hatası: {e}")
            return {'results': [], 'total_count': 0, 'error': str(e)}
    
    def parse_html_results(self, html_content, page):
        """HTML sonuçlarını parse et"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            results = []
            
            # Tablo satırlarını bul
            result_rows = soup.find_all('tr', class_=['odd', 'even']) or soup.find_all('tr')[1:]  # İlk satır başlık
            
            for row in result_rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    # İlk hücre: Mevzuat No
                    first_cell = cells[0]
                    link = first_cell.find('a')
                    
                    if link:
                        mevzuat_no = link.get_text(strip=True)
                        detail_url = link.get('href', '')
                        
                        # İkinci hücre: Başlık
                        second_cell = cells[1]
                        title_link = second_cell.find('a')
                        title = title_link.get_text(strip=True) if title_link else second_cell.get_text(strip=True)
                        
                        params = self.parse_mevzuat_url(detail_url)
                        
                        result = {
                            'mevzuat_no': mevzuat_no,
                            'title': self.clean_html(title),
                            'detail_url': urljoin(self.BASE_URL, detail_url),
                            'pdf_url': self.generate_pdf_url(params),
                            'mevzuat_tur': params.get('MevzuatTur'),
                            'mevzuat_tertip': params.get('MevzuatTertip'),
                            'type': 'Mevzuat'
                        }
                        results.append(result)
            
            return {
                'results': results,
                'total_count': len(results) if results else 0,
                'has_next': len(results) == 10,
                'has_previous': page > 1,
                'current_page': page,
                'total_pages': 1,
                'error': None
            }
            
        except Exception as e:
            print(f"HTML parse hatası: {e}")
            return {'results': [], 'total_count': 0, 'error': str(e)}
    
    def parse_mevzuat_url(self, url):
        """URL'den parametreleri çıkar"""
        try:
            parsed_url = urlparse(url)
            params = parse_qs(parsed_url.query)
            return {
                'MevzuatNo': params.get('MevzuatNo', [None])[0],
                'MevzuatTur': params.get('MevzuatTur', [None])[0],
                'MevzuatTertip': params.get('MevzuatTertip', [None])[0],
            }
        except:
            return {}
    
    def generate_pdf_url(self, params):
        """PDF URL oluştur"""
        try:
            mevzuat_tur = params.get('MevzuatTur')
            mevzuat_tertip = params.get('MevzuatTertip')
            mevzuat_no = params.get('MevzuatNo')
            
            if all([mevzuat_tur, mevzuat_tertip, mevzuat_no]):
                return f"{self.BASE_URL}/MevzuatMetin/{mevzuat_tur}.{mevzuat_tertip}.{mevzuat_no}.pdf"
        except:
            pass
        return None
    
    def clean_html(self, text):
        """HTML temizle"""
        if not text:
            return ""
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

# Test
if __name__ == "__main__":
    service = FixedMevzuatService()
    result = service.search_legislation("medeni", 1)
    print(f"Results found: {len(result['results'])}")
    if result['results']:
        print(f"First result: {result['results'][0]['title']}")
    if result['error']:
        print(f"Error: {result['error']}")