import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re

logger = logging.getLogger(__name__)

class SeleniumMevzuatService:
    """Selenium ile mevzuat.gov.tr arama servisi"""
    
    BASE_URL = "https://www.mevzuat.gov.tr"
    
    def __init__(self, headless=True):
        self.headless = headless
        self.driver = None
        
    def _setup_driver(self):
        """Chrome WebDriver kurulumu"""
        if self.driver:
            return
            
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_page_load_timeout(30)
        except Exception as e:
            logger.error(f"WebDriver kurulum hatası: {e}")
            raise
    
    def search_legislation(self, query, page=1):
        """Mevzuat arama - Selenium ile"""
        try:
            self._setup_driver()
            
            # Ana sayfaya git
            logger.info(f"Navigating to {self.BASE_URL}")
            self.driver.get(self.BASE_URL)
            
            # Arama kutusunu bul ve doldur
            search_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "AranacakMetin"))
            )
            search_input.clear()
            search_input.send_keys(query)
            
            # Arama butonuna tıkla
            search_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit']")
            search_button.click()
            
            # Sonuçların yüklenmesini bekle
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.ID, "Baslik_Datatable"))
            )
            
            # DataTable'ın yüklenmesini bekle
            time.sleep(3)
            
            # Sayfa kaynağını al
            page_source = self.driver.page_source
            
            # Sonuçları parse et
            return self._parse_results(page_source, query, page)
            
        except TimeoutException:
            logger.error("Selenium timeout - sayfa yüklenemedi")
            return self._empty_result(page, "Arama sayfası yüklenemedi")
        except Exception as e:
            logger.error(f"Selenium arama hatası: {e}")
            return self._empty_result(page, str(e))
        finally:
            if self.driver:
                self.driver.quit()
                self.driver = None
    
    def _parse_results(self, html_content, query, page):
        """HTML sonuçlarını parse et"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            results = []
            
            # DataTable tbody'sini bul
            table = soup.find('table', {'id': 'Baslik_Datatable'})
            if not table:
                logger.warning("DataTable bulunamadı")
                return self._empty_result(page, "Sonuç tablosu bulunamadı")
            
            tbody = table.find('tbody')
            if not tbody:
                logger.warning("tbody bulunamadı")
                return self._empty_result(page, "Sonuç satırları bulunamadı")
            
            rows = tbody.find_all('tr')
            logger.info(f"Found {len(rows)} result rows")
            
            for i, row in enumerate(rows):
                try:
                    cells = row.find_all('td')
                    if len(cells) >= 2:
                        result = self._parse_result_row(cells)
                        if result:
                            results.append(result)
                            logger.info(f"Parsed result {i+1}: {result['mevzuat_no']} - {result['title'][:50]}...")
                except Exception as e:
                    logger.error(f"Satır {i} parse hatası: {e}")
                    continue
            
            # Toplam sayı bilgisini al
            total_count = self._extract_total_count(soup)
            
            # Sayfalama hesapla
            per_page = 10
            total_pages = max(1, (total_count + per_page - 1) // per_page) if total_count > 0 else 1
            
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
            return self._empty_result(page, str(e))
    
    def _parse_result_row(self, cells):
        """Tek bir sonuç satırını parse et"""
        try:
            # İlk hücre: Mevzuat No ve Link
            first_cell = cells[0]
            mevzuat_link = first_cell.find('a')
            
            if not mevzuat_link:
                return None
            
            mevzuat_no = mevzuat_link.get_text(strip=True)
            detail_url = mevzuat_link.get('href', '')
            
            # İkinci hücre: Başlık ve Meta bilgiler
            second_cell = cells[1]
            
            # Başlığı bul
            title_element = second_cell.find('a')
            if not title_element:
                title_element = second_cell.find('div')
            
            if title_element:
                title = self._clean_html(title_element.get_text())
            else:
                title = self._clean_html(second_cell.get_text())
            
            # URL parametrelerini parse et
            params = self._parse_mevzuat_url(detail_url)
            
            # Meta bilgileri
            meta_div = second_cell.find('div', class_=['mt-1', 'small', 'text-muted'])
            meta_info = {}
            
            if meta_div:
                meta_text = meta_div.get_text()
                meta_info = self._parse_meta_text(meta_text)
            
            # PDF URL oluştur
            pdf_url = self._generate_pdf_url(params)
            
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
    
    def _parse_meta_text(self, meta_text):
        """Meta metin bilgilerini parse et"""
        meta_info = {}
        
        try:
            # Mevzuat türü
            if 'Kanunlar' in meta_text:
                meta_info['type'] = 'Kanun'
            elif 'Tebliğler' in meta_text:
                meta_info['type'] = 'Tebliğ'
            elif 'Yönetmelikler' in meta_text:
                meta_info['type'] = 'Yönetmelik'
            elif 'Cumhurbaşkanı Kararları' in meta_text:
                meta_info['type'] = 'Cumhurbaşkanı Kararı'
            else:
                meta_info['type'] = 'Mevzuat'
            
            # Tertip
            tertip_match = re.search(r'Tertip[:\s]*(\d+)', meta_text)
            if tertip_match:
                meta_info['tertip'] = tertip_match.group(1)
            
            # Resmi Gazete Tarihi
            rg_tarih_match = re.search(r'Resmî?\s*Gazete\s*Tarihi[:\s]*(\d{2}[./]\d{2}[./]\d{4})', meta_text)
            if rg_tarih_match:
                meta_info['resmi_gazete_tarihi'] = rg_tarih_match.group(1)
            
            # Resmi Gazete Sayısı
            rg_sayi_match = re.search(r'Sayısı[:\s]*(\d+)', meta_text)
            if rg_sayi_match:
                meta_info['resmi_gazete_sayisi'] = rg_sayi_match.group(1)
            
            # Kabul Tarihi
            kabul_match = re.search(r'Kabul\s*Tarihi[:\s]*(\d{2}[./]\d{2}[./]\d{4})', meta_text)
            if kabul_match:
                meta_info['kabul_tarihi'] = kabul_match.group(1)
        
        except Exception as e:
            logger.error(f"Meta parse error: {e}")
        
        return meta_info
    
    def _parse_mevzuat_url(self, url):
        """URL parametrelerini parse et"""
        try:
            from urllib.parse import urlparse, parse_qs
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
    
    def _generate_pdf_url(self, params):
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
    
    def _extract_total_count(self, soup):
        """Toplam sonuç sayısını çıkar"""
        try:
            # DataTables info div'ini ara
            info_div = soup.find('div', class_='dataTables_info')
            if info_div:
                info_text = info_div.get_text()
                match = re.search(r'(\d+)\s*[Kk]ayıttan', info_text)
                if match:
                    return int(match.group(1))
        except:
            pass
        return 0
    
    def _clean_html(self, text):
        """HTML temizle"""
        if not text:
            return ""
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def _empty_result(self, page, error=None):
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
    
    def __del__(self):
        """Cleanup"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass

# Test
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    service = SeleniumMevzuatService(headless=True)
    result = service.search_legislation("medeni", 1)
    
    print(f"Results found: {len(result['results'])}")
    print(f"Total count: {result['total_count']}")
    
    if result['results']:
        for i, res in enumerate(result['results'][:3]):
            print(f"{i+1}. {res['mevzuat_no']} - {res['title'][:80]}...")
            print(f"   PDF: {res['pdf_url']}")
    
    if result['error']:
        print(f"Error: {result['error']}")