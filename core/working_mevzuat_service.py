import requests
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin, parse_qs, urlparse
import logging

logger = logging.getLogger(__name__)

class WorkingMevzuatService:
    """Çalışan mevzuat.gov.tr servisi - HTML parse"""
    
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
            'Sec-Fetch-Site': 'same-origin'
        })
    
    def get_token(self):
        """Ana sayfadan token al"""
        try:
            response = self.session.get(self.BASE_URL)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            token_input = soup.find('input', {'name': 'antiforgerytoken'})
            
            if token_input:
                return token_input.get('value')
            
            return None
            
        except Exception as e:
            logger.error(f"Token alma hatası: {e}")
            return None
    
    def search_legislation(self, query, page=1):
        """Mevzuat arama - Artık HTML parse ile çalışan versiyon"""
        try:
            token = self.get_token()
            
            # Form data
            form_data = {
                'AranacakMetin': query,
                'antiforgerytoken': token or ''
            }
            
            # Arama yap
            response = self.session.post(
                f"{self.BASE_URL}/aramasonuc",
                data=form_data,
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Referer': self.BASE_URL,
                    'X-Requested-With': 'XMLHttpRequest'
                }
            )
            
            if response.status_code == 200:
                return self.parse_search_results(response.content, query, page)
            else:
                return self.empty_result(page, f"HTTP {response.status_code}")
                
        except Exception as e:
            logger.error(f"Arama hatası: {e}")
            return self.empty_result(page, str(e))
    
    def parse_search_results(self, html_content, query, page=1):
        """HTML'den sonuçları parse et"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            results = []
            
            # DataTable tbody'sini bul
            table = soup.find('table', {'id': 'Baslik_Datatable'})
            if not table:
                # Alternatif olarak class ile ara
                table = soup.find('table', class_='filter-table')
            
            if table:
                tbody = table.find('tbody')
                if tbody:
                    rows = tbody.find_all('tr')
                    
                    for row in rows:
                        try:
                            cells = row.find_all('td')
                            if len(cells) >= 2:
                                result = self.parse_result_row(cells)
                                if result:
                                    results.append(result)
                        except Exception as e:
                            logger.error(f"Satır parse hatası: {e}")
                            continue
            
            # Eğer DataTable yoksa, alternatif tr yapısını dene
            if not results:
                rows = soup.find_all('tr', class_=['odd', 'even'])
                for row in rows:
                    try:
                        cells = row.find_all('td')
                        if len(cells) >= 2:
                            result = self.parse_result_row(cells)
                            if result:
                                results.append(result)
                    except Exception as e:
                        continue
            
            # Toplam sayı bilgisini al
            total_count = self.extract_total_count(soup)
            
            # Sayfalama hesapla
            total_pages = max(1, (total_count + 9) // 10) if total_count > 0 else 1
            
            return {
                'results': results,
                'total_count': total_count or len(results),
                'has_next': page < total_pages,
                'has_previous': page > 1,
                'current_page': page,
                'total_pages': total_pages,
                'error': None
            }
            
        except Exception as e:
            logger.error(f"HTML parse hatası: {e}")
            return self.empty_result(page, str(e))
    
    def parse_result_row(self, cells):
        """Tek bir sonuç satırını parse et"""
        try:
            # İlk hücre: Mevzuat No ve Link
            first_cell = cells[0]
            mevzuat_link = first_cell.find('a')
            
            if not mevzuat_link:
                return None
            
            mevzuat_no = mevzuat_link.get_text(strip=True)
            detail_url = mevzuat_link.get('href', '')
            
            # URL parametrelerini parse et
            params = self.parse_mevzuat_url(detail_url)
            
            # İkinci hücre: Başlık ve Meta bilgiler
            second_cell = cells[1]
            title_link = second_cell.find('a')
            
            if not title_link:
                return None
            
            # Başlık
            title_div = title_link.find('div')
            title = self.clean_html(title_div.get_text() if title_div else title_link.get_text())
            
            # Meta bilgileri
            meta_div = second_cell.find('div', class_=['mt-1', 'small'])
            meta_info = {}
            
            if meta_div:
                meta_text = meta_div.get_text()
                meta_info = self.parse_meta_text(meta_text)
            
            # PDF URL oluştur
            pdf_url = self.generate_pdf_url(params)
            
            return {
                'mevzuat_no': mevzuat_no,
                'title': title,
                'detail_url': urljoin(self.BASE_URL, detail_url) if not detail_url.startswith('http') else detail_url,
                'pdf_url': pdf_url,
                'mevzuat_tur': params.get('MevzuatTur'),
                'mevzuat_tertip': params.get('MevzuatTertip'),
                **meta_info
            }
            
        except Exception as e:
            logger.error(f"Row parse error: {e}")
            return None
    
    def parse_meta_text(self, meta_text):
        """Meta metin bilgilerini parse et"""
        meta_info = {}
        
        try:
            # Mevzuat türü (italic text)
            if 'Kanunlar' in meta_text:
                meta_info['type'] = 'Kanun'
            elif 'Tebliğler' in meta_text:
                meta_info['type'] = 'Tebliğ'
            elif 'Yönetmelikler' in meta_text:
                meta_info['type'] = 'Yönetmelik'
            elif 'Cumhurbaşkanı Kararları' in meta_text:
                meta_info['type'] = 'Cumhurbaşkanı Kararı'
            
            # Tertip
            tertip_match = re.search(r'Tertip:\s*(\d+)', meta_text)
            if tertip_match:
                meta_info['tertip'] = tertip_match.group(1)
            
            # Resmi Gazete Tarihi
            rg_tarih_match = re.search(r'Resmî Gazete Tarihi:\s*(\d{2}\.\d{2}\.\d{4})', meta_text)
            if rg_tarih_match:
                meta_info['resmi_gazete_tarihi'] = rg_tarih_match.group(1)
            
            # Resmi Gazete Sayısı
            rg_sayi_match = re.search(r'Sayısı:\s*(\d+)', meta_text)
            if rg_sayi_match:
                meta_info['resmi_gazete_sayisi'] = rg_sayi_match.group(1)
            
            # Kabul Tarihi
            kabul_match = re.search(r'Kabul Tarihi:\s*(\d{2}\.\d{2}\.\d{4})', meta_text)
            if kabul_match:
                meta_info['kabul_tarihi'] = kabul_match.group(1)
        
        except Exception as e:
            logger.error(f"Meta parse error: {e}")
        
        return meta_info
    
    def parse_mevzuat_url(self, url):
        """URL parametrelerini parse et"""
        try:
            if '?' in url:
                parsed = urlparse(url)
                params = parse_qs(parsed.query)
                return {
                    'MevzuatNo': params.get('MevzuatNo', [None])[0],
                    'MevzuatTur': params.get('MevzuatTur', [None])[0],
                    'MevzuatTertip': params.get('MevzuatTertip', [None])[0],
                }
        except:
            pass
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
    
    def extract_total_count(self, soup):
        """Toplam sonuç sayısını çıkar"""
        try:
            # "X Kayıttan" formatını ara
            info_div = soup.find('div', class_='dataTables_info')
            if info_div:
                info_text = info_div.get_text()
                match = re.search(r'(\d+)\s*Kayıttan', info_text)
                if match:
                    return int(match.group(1))
            
            # Alternatif: tablo satır sayısından hesapla
            table = soup.find('table', {'id': 'Baslik_Datatable'})
            if table:
                tbody = table.find('tbody')
                if tbody:
                    rows = tbody.find_all('tr')
                    return len(rows)
        
        except:
            pass
        
        return 0
    
    def clean_html(self, text):
        """HTML temizle"""
        if not text:
            return ""
        
        # HTML taglerini kaldır
        text = re.sub(r'<[^>]+>', '', text)
        # Fazla boşlukları temizle
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def empty_result(self, page, error=None):
        """Boş sonuç döndür"""
        return {
            'results': [],
            'total_count': 0,
            'has_next': False,
            'has_previous': page > 1,
            'current_page': page,
            'total_pages': 1,
            'error': error
        }

# Test
if __name__ == "__main__":
    service = WorkingMevzuatService()
    result = service.search_legislation("ticaret", 1)
    
    print(f"Results found: {len(result['results'])}")
    print(f"Total count: {result['total_count']}")
    
    if result['results']:
        for i, res in enumerate(result['results'][:3]):
            print(f"{i+1}. {res['mevzuat_no']} - {res['title'][:80]}...")
            print(f"   PDF: {res['pdf_url']}")
    
    if result['error']:
        print(f"Error: {result['error']}")