import requests
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin, parse_qs, urlparse
import logging

logger = logging.getLogger(__name__)

class MevzuatService:
    """Mevzuat.gov.tr ile entegrasyon servisi"""
    
    BASE_URL = "https://www.mevzuat.gov.tr"
    SEARCH_URL = f"{BASE_URL}/aramasonuc"
    DETAIL_URL = f"{BASE_URL}/mevzuat"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'tr-TR,tr;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
    
    def get_antiforgery_token(self):
        """Ana sayfadan anti-forgery token'ı al"""
        try:
            response = self.session.get(self.BASE_URL)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            token_input = soup.find('input', {'name': 'antiforgerytoken'})
            
            if token_input:
                return token_input.get('value')
            
            # Alternatif olarak __RequestVerificationToken arıyoruz
            token_input = soup.find('input', {'name': '__RequestVerificationToken'})
            if token_input:
                return token_input.get('value')
            
            logger.warning("Anti-forgery token bulunamadı")
            return None
            
        except Exception as e:
            logger.error(f"Token alma hatası: {e}")
            return None
    
    def search_legislation(self, query, page=1):
        """Mevzuat.gov.tr'de arama yap"""
        try:
            # Anti-forgery token'ı al
            token = self.get_antiforgery_token()
            
            # Arama verilerini hazırla
            search_data = {
                'AranacakMetin': query,
                'draw': page,
                'start': (page - 1) * 10,
                'length': 10,
            }
            
            if token:
                search_data['antiforgerytoken'] = token
            
            # Arama yap
            response = self.session.post(
                self.SEARCH_URL,
                data=search_data,
                timeout=30
            )
            response.raise_for_status()
            
            # Sonuçları parse et
            return self.parse_search_results(response.content, page)
            
        except Exception as e:
            logger.error(f"Arama hatası: {e}")
            return {
                'results': [],
                'total_count': 0,
                'has_next': False,
                'has_previous': False,
                'current_page': page,
                'error': str(e)
            }
    
    def parse_search_results(self, html_content, current_page):
        """Arama sonuçlarını parse et"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            results = []
            
            # Sonuç satırlarını bul
            result_rows = soup.find_all('tr', class_=['odd', 'even'])
            
            for row in result_rows:
                try:
                    cells = row.find_all('td')
                    if len(cells) < 2:
                        continue
                    
                    # Mevzuat numarası ve link
                    first_cell = cells[0]
                    link_element = first_cell.find('a')
                    
                    if not link_element:
                        continue
                    
                    mevzuat_no = link_element.text.strip()
                    detail_url = link_element.get('href', '')
                    
                    # URL parametrelerini parse et
                    params = self.parse_mevzuat_url(detail_url)
                    
                    # Başlık ve meta bilgiler
                    second_cell = cells[1]
                    title_element = second_cell.find('a')
                    
                    if not title_element:
                        continue
                    
                    # Başlığı temizle (HTML taglerini kaldır)
                    title_div = title_element.find('div')
                    if title_div:
                        title = self.clean_html(title_div.get_text())
                    else:
                        title = self.clean_html(title_element.get_text())
                    
                    # Meta bilgileri parse et
                    meta_div = second_cell.find('div', class_='mt-1')
                    meta_info = self.parse_meta_info(meta_div) if meta_div else {}
                    
                    # PDF URL'sini oluştur
                    pdf_url = self.generate_pdf_url(params)
                    
                    result = {
                        'mevzuat_no': mevzuat_no,
                        'title': title,
                        'detail_url': urljoin(self.BASE_URL, detail_url),
                        'pdf_url': pdf_url,
                        'mevzuat_tur': params.get('MevzuatTur'),
                        'mevzuat_tertip': params.get('MevzuatTertip'),
                        **meta_info
                    }
                    
                    results.append(result)
                    
                except Exception as e:
                    logger.error(f"Sonuç parse hatası: {e}")
                    continue
            
            # Sayfalama bilgilerini hesapla
            total_info = soup.find('div', class_='dataTables_info')
            total_count = self.extract_total_count(total_info)
            
            has_next = len(results) == 10 and (current_page * 10) < total_count
            has_previous = current_page > 1
            
            return {
                'results': results,
                'total_count': total_count,
                'has_next': has_next,
                'has_previous': has_previous,
                'current_page': current_page,
                'total_pages': (total_count + 9) // 10,  # Yukarı yuvarlama
                'error': None
            }
            
        except Exception as e:
            logger.error(f"Parse hatası: {e}")
            return {
                'results': [],
                'total_count': 0,
                'has_next': False,
                'has_previous': False,
                'current_page': current_page,
                'error': str(e)
            }
    
    def parse_mevzuat_url(self, url):
        """Mevzuat URL'sinden parametreleri çıkar"""
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
    
    def parse_meta_info(self, meta_div):
        """Meta bilgileri parse et"""
        if not meta_div:
            return {}
        
        meta_text = meta_div.get_text()
        meta_info = {}
        
        try:
            # Mevzuat türü
            if 'Kanunlar' in meta_text:
                meta_info['type'] = 'Kanun'
            elif 'Yönetmelik' in meta_text:
                meta_info['type'] = 'Yönetmelik'
            elif 'Tebliğ' in meta_text:
                meta_info['type'] = 'Tebliğ'
            elif 'Genelge' in meta_text:
                meta_info['type'] = 'Genelge'
            else:
                # İlk italic metni al
                type_match = re.search(r'<i>(.*?)</i>', str(meta_div))
                if type_match:
                    meta_info['type'] = type_match.group(1).strip()
            
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
            kabul_tarih_match = re.search(r'Kabul Tarihi:\s*(\d{2}\.\d{2}\.\d{4})', meta_text)
            if kabul_tarih_match:
                meta_info['kabul_tarihi'] = kabul_tarih_match.group(1)
                
        except Exception as e:
            logger.error(f"Meta parse hatası: {e}")
        
        return meta_info
    
    def generate_pdf_url(self, params):
        """PDF URL'sini oluştur"""
        try:
            mevzuat_tur = params.get('MevzuatTur')
            mevzuat_tertip = params.get('MevzuatTertip')
            mevzuat_no = params.get('MevzuatNo')
            
            if all([mevzuat_tur, mevzuat_tertip, mevzuat_no]):
                return f"{self.BASE_URL}/MevzuatMetin/{mevzuat_tur}.{mevzuat_tertip}.{mevzuat_no}.pdf"
        except:
            pass
        
        return None
    
    def extract_total_count(self, info_div):
        """Toplam sonuç sayısını çıkar"""
        if not info_div:
            return 0
        
        try:
            info_text = info_div.get_text()
            # "X Kayıttan" formatını ara
            match = re.search(r'(\d+)\s*Kayıttan', info_text)
            if match:
                return int(match.group(1))
        except:
            pass
        
        return 0
    
    def clean_html(self, text):
        """HTML taglerini ve gereksiz boşlukları temizle"""
        if not text:
            return ""
        
        # HTML taglerini kaldır
        text = re.sub(r'<[^>]+>', '', text)
        
        # Fazla boşlukları temizle
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def get_mevzuat_detail(self, mevzuat_no, mevzuat_tur, mevzuat_tertip):
        """Mevzuat detayını al"""
        try:
            detail_url = f"{self.DETAIL_URL}?MevzuatNo={mevzuat_no}&MevzuatTur={mevzuat_tur}&MevzuatTertip={mevzuat_tertip}"
            
            response = self.session.get(detail_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # PDF linkini bul
            pdf_link = soup.find('a', {'href': lambda x: x and '.pdf' in x})
            pdf_url = None
            if pdf_link:
                pdf_url = urljoin(self.BASE_URL, pdf_link['href'])
            
            # Word linkini bul
            word_link = soup.find('a', {'href': lambda x: x and '.doc' in x})
            word_url = None
            if word_link:
                word_url = urljoin(self.BASE_URL, word_link['href'])
            
            # Resmi Gazete bilgilerini al
            rg_info = soup.find('div', class_='font-italic small')
            rg_text = rg_info.get_text() if rg_info else ""
            
            return {
                'pdf_url': pdf_url,
                'word_url': word_url,
                'resmi_gazete_info': rg_text,
                'detail_url': detail_url
            }
            
        except Exception as e:
            logger.error(f"Detay alma hatası: {e}")
            return None

# Service instance
mevzuat_service = MevzuatService()