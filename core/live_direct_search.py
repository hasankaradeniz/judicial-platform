# core/live_direct_search.py

import time
import re
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from django.core.cache import cache
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

class DirectLiveMevzuatSearcher:
    """Doğrudan mevzuat.gov.tr'den arama yapan ve sanki kendi uygulamamızda arama yapılıyormuş gibi gösteren sınıf"""
    
    def __init__(self, cache_timeout=1800):  # 30 dakika cache
        self.cache_timeout = cache_timeout
        self.base_url = "https://www.mevzuat.gov.tr"
        
    def search_legislation(self, query, mevzuat_type=None, page=1, per_page=20):
        """
        Doğrudan mevzuat.gov.tr'den arama yap
        Sonuçları kendi uygulamamızda gösterilecek formatta döndür
        """
        try:
            # Cache kontrolü
            cache_key = self._generate_cache_key(query, mevzuat_type, page)
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.info(f"Cache'den sonuç döndürüldü: {query} (sayfa {page})")
                return cached_result
            
            # Selenium ile arama yap
            results = self._perform_live_search(query, mevzuat_type, page, per_page)
            
            # Sonuçları cache'e kaydet
            if results:
                cache.set(cache_key, results, self.cache_timeout)
                logger.info(f"Sonuçlar cache'e kaydedildi: {query} - {len(results.get('results', []))} sonuç")
            
            return results
            
        except Exception as e:
            logger.error(f"Direct live search error: {str(e)}")
            return {
                'results': [],
                'total_count': 0,
                'page': page,
                'per_page': per_page,
                'has_next': False,
                'has_previous': False,
                'error': str(e)
            }
    
    def _generate_cache_key(self, query, mevzuat_type, page):
        """Cache key oluştur"""
        safe_query = ''.join(c for c in query if c.isalnum() or c in ' -_').strip()[:50]
        safe_type = mevzuat_type or 'all'
        return f"direct_live_{safe_query}_{safe_type}_p{page}".replace(' ', '_')
    
    def _perform_live_search(self, query, mevzuat_type, page, per_page):
        """Selenium ile canlı arama gerçekleştir - İyileştirilmiş"""
        driver = None
        try:
            # Chrome ayarları - daha stabil
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
            
            # WebDriver oluştur
            try:
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=chrome_options)
            except:
                driver = webdriver.Chrome(options=chrome_options)
            
            # Anti-detection
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # Timeout ayarları
            driver.implicitly_wait(10)
            driver.set_page_load_timeout(30)
            
            # Birden fazla URL stratejisi deneyelim
            search_strategies = [
                # Strateji 1: Gelişmiş arama sayfası
                {
                    'url': 'https://www.mevzuat.gov.tr/MevzuatArama',
                    'method': 'advanced_form'
                },
                # Strateji 2: Basit arama sayfası
                {
                    'url': 'https://www.mevzuat.gov.tr/mevzuat',
                    'method': 'simple_form'
                },
                # Strateji 3: Direkt GET parametreli URL
                {
                    'url': f'https://www.mevzuat.gov.tr/mevzuat?Criteria.SearchText={query}',
                    'method': 'direct_url'
                },
                # Strateji 4: Ana sayfa araması
                {
                    'url': f'https://www.mevzuat.gov.tr/?s={query}',
                    'method': 'home_search'
                }
            ]
            
            results = None
            for strategy in search_strategies:
                try:
                    logger.info(f"Strateji deneniyor: {strategy['method']} - {strategy['url']}")
                    
                    # Sayfaya git
                    driver.get(strategy['url'])
                    time.sleep(3)
                    
                    # Sayfa yüklenip yüklenmediğini kontrol et
                    if "404" in driver.page_source or "bulunamadı" in driver.page_source.lower():
                        logger.warning(f"Sayfa bulunamadı: {strategy['url']}")
                        continue
                    
                    # Yöntemini uygula
                    success = False
                    if strategy['method'] == 'advanced_form':
                        success = self._try_advanced_form_search(driver, query, mevzuat_type)
                    elif strategy['method'] == 'simple_form':
                        success = self._try_simple_form_search(driver, query, mevzuat_type)
                    elif strategy['method'] in ['direct_url', 'home_search']:
                        success = True  # URL zaten parametreli
                    
                    if success:
                        # Sonuçları bekle
                        time.sleep(5)
                        
                        # Sonuçları parse et
                        results = self._parse_search_results(driver, page, per_page)
                        
                        if results and results['total_count'] > 0:
                            logger.info(f"Başarılı strateji: {strategy['method']} - {results['total_count']} sonuç")
                            break
                        else:
                            logger.warning(f"Strateji sonuç vermedi: {strategy['method']}")
                    
                except Exception as e:
                    logger.error(f"Strateji {strategy['method']} hatası: {str(e)}")
                    continue
            
            # Hiçbir strateji çalışmadıysa boş sonuç döndür
            if not results or results['total_count'] == 0:
                logger.warning("Hiçbir arama stratejisi başarılı olmadı")
                results = {
                    'results': [],
                    'total_count': 0,
                    'page': page,
                    'per_page': per_page,
                    'has_next': False,
                    'has_previous': False,
                    'error': 'Arama sonucu bulunamadı'
                }
            
            return results
            
        except Exception as e:
            logger.error(f"Live search error: {str(e)}")
            return {
                'results': [],
                'total_count': 0,
                'page': page,
                'per_page': per_page,
                'has_next': False,
                'has_previous': False,
                'error': str(e)
            }
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
    
    def _select_mevzuat_type(self, driver, mevzuat_type):
        """Mevzuat türü seçimi"""
        try:
            # Mevzuat türü mapping
            type_mapping = {
                '1': 'Kanun',
                '2': 'Cumhurbaşkanlığı Kararnamesi', 
                '5': 'Yönetmelik',
                '6': 'Tüzük',
                '7': 'Tebliğ',
                '8': 'Genelge',
                '9': 'Uluslararası Anlaşma'
            }
            
            type_name = type_mapping.get(mevzuat_type, '')
            if type_name:
                # Dropdown'u bul ve seç
                type_select = Select(driver.find_element(By.NAME, "Criteria.MevzuatTuru"))
                type_select.select_by_visible_text(type_name)
                
        except Exception as e:
            logger.warning(f"Mevzuat türü seçimi başarısız: {str(e)}")
    
    def _try_advanced_form_search(self, driver, query, mevzuat_type):
        """Gelişmiş arama formu deneme"""
        try:
            # Gelişmiş arama formu elementlerini bul
            search_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='text']")
            
            # En uygun arama kutusunu bul
            search_input = None
            for inp in search_inputs:
                name = inp.get_attribute('name') or ''
                placeholder = inp.get_attribute('placeholder') or ''
                if any(keyword in name.lower() for keyword in ['search', 'text', 'ara']) or \
                   any(keyword in placeholder.lower() for keyword in ['ara', 'search']):
                    search_input = inp
                    break
            
            if not search_input and search_inputs:
                search_input = search_inputs[0]  # İlk input'u kullan
            
            if search_input:
                search_input.clear()
                search_input.send_keys(query)
                
                # Mevzuat türü seçimi
                if mevzuat_type:
                    self._select_mevzuat_type(driver, mevzuat_type)
                
                # Submit butonunu bul ve tıkla
                submit_buttons = driver.find_elements(By.CSS_SELECTOR, 
                    "input[type='submit'], button[type='submit'], button:contains('Ara'), input[value*='Ara']")
                
                if submit_buttons:
                    submit_buttons[0].click()
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Advanced form search error: {str(e)}")
            return False
    
    def _try_simple_form_search(self, driver, query, mevzuat_type):
        """Basit arama formu deneme"""
        try:
            # Basit arama formu elementlerini bul
            possible_names = ['Criteria.SearchText', 'searchText', 'q', 'search', 'query']
            search_input = None
            
            for name in possible_names:
                try:
                    search_input = driver.find_element(By.NAME, name)
                    break
                except:
                    continue
            
            # ID ile deneme
            if not search_input:
                possible_ids = ['searchText', 'search', 'query', 'q']
                for id_name in possible_ids:
                    try:
                        search_input = driver.find_element(By.ID, id_name)
                        break
                    except:
                        continue
            
            # CSS selector ile deneme
            if not search_input:
                try:
                    search_input = driver.find_element(By.CSS_SELECTOR, "input[type='text']:first-of-type")
                except:
                    pass
            
            if search_input:
                search_input.clear()
                search_input.send_keys(query)
                
                # Mevzuat türü seçimi
                if mevzuat_type:
                    self._select_mevzuat_type(driver, mevzuat_type)
                
                # Submit butonunu bul
                try:
                    submit_button = driver.find_element(By.CSS_SELECTOR, "input[type='submit'], button[type='submit']")
                    submit_button.click()
                    return True
                except:
                    # Form submit deneme
                    try:
                        search_input.submit()
                        return True
                    except:
                        pass
            
            return False
            
        except Exception as e:
            logger.error(f"Simple form search error: {str(e)}")
            return False
    
    def _parse_search_results(self, driver, page, per_page):
        """Arama sonuçlarını parse et - İyileştirilmiş mevzuat.gov.tr için"""
        try:
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            results = []
            
            # Debug: Sayfayı incele
            logger.info("Sayfa parse ediliyor...")
            
            # Mevzuat.gov.tr'deki gerçek sonuç elementlerini bul
            # 1. Önce tablo formatındaki sonuçları ara
            result_elements = []
            
            # Tablo satırlarını kontrol et
            table_rows = soup.find_all('tr')
            for row in table_rows:
                # Mevzuat linklerini içeren satırları bul
                links = row.find_all('a', href=re.compile(r'(MevzuatMetin|mevzuat.*No=)', re.I))
                if links:
                    # Header/navbar linklerini filtrele
                    is_nav_link = False
                    for parent in row.parents:
                        if parent.name and ('nav' in parent.get('class', []) or 'header' in parent.get('class', []) or 'menu' in parent.get('class', [])):
                            is_nav_link = True
                            break
                    
                    if not is_nav_link:
                        result_elements.append(row)
            
            # 2. Div formatındaki sonuçları ara
            if not result_elements:
                div_elements = soup.find_all('div', class_=re.compile(r'(search|result|item)', re.I))
                for div in div_elements:
                    links = div.find_all('a', href=re.compile(r'(MevzuatMetin|mevzuat.*No=)', re.I))
                    if links:
                        # Header/navbar kontrolü
                        is_nav_div = False
                        for parent in div.parents:
                            if parent.name and ('nav' in parent.get('class', []) or 'header' in parent.get('class', []) or 'menu' in parent.get('class', [])):
                                is_nav_div = True
                                break
                        
                        if not is_nav_div:
                            result_elements.append(div)
            
            # 3. Son çare: Tüm mevzuat linklerini bul ve parent elementlerini al
            if not result_elements:
                mevzuat_links = soup.find_all('a', href=re.compile(r'(MevzuatMetin|mevzuat.*No=)', re.I))
                seen_parents = set()
                
                for link in mevzuat_links:
                    # Link parent'ını bul
                    parent = link.parent
                    while parent and parent.name in ['span', 'strong', 'b', 'em']:
                        parent = parent.parent
                    
                    if parent and parent not in seen_parents:
                        # Header/navbar kontrolü
                        is_nav_link = False
                        for ancestor in parent.parents:
                            if ancestor.name and ('nav' in ancestor.get('class', []) or 
                                                'header' in ancestor.get('class', []) or 
                                                'menu' in ancestor.get('class', []) or
                                                'navbar' in ancestor.get('class', [])):
                                is_nav_link = True
                                break
                        
                        # İçerik kontrolü - gerçek mevzuat başlıkları genelde uzundur
                        link_text = link.get_text(strip=True)
                        if (not is_nav_link and 
                            len(link_text) > 10 and  # Kısa nav linklerini filtrele
                            not any(nav_word in link_text.lower() for nav_word in ['anasayfa', 'giriş', 'menü', 'arama', 'hakkında'])):
                            result_elements.append(parent)
                            seen_parents.add(parent)
            
            # Header/navbar elementlerini filtrele
            filtered_results = []
            for element in result_elements:
                element_text = element.get_text(strip=True)
                
                # Navigation kelimeleri kontrolü
                nav_indicators = [
                    'anasayfa', 'ana sayfa', 'giriş yap', 'kayıt ol', 'hakkımızda',
                    'iletişim', 'menü', 'arama yap', 'gelişmiş arama', 'yardım',
                    'site haritası', 'rss', 'mobil', 'favoriler', 'mevzuat bilgi sistemi',
                    'kullanıcı rehberi', 'sık sorulan', 'gizlilik', 'yasal uyarı'
                ]
                
                is_nav_element = any(indicator in element_text.lower() for indicator in nav_indicators)
                
                # Çok kısa veya çok uzun içerikleri filtrele
                if (not is_nav_element and 
                    20 < len(element_text) < 5000 and  # Uygun uzunluk
                    ('kanun' in element_text.lower() or 
                     'yönetmelik' in element_text.lower() or 
                     'tüzük' in element_text.lower() or 
                     'kararname' in element_text.lower() or
                     'tebliğ' in element_text.lower() or
                     'genelge' in element_text.lower() or
                     any(char.isdigit() for char in element_text))):  # Sayı içeriyor (mevzuat no)
                    filtered_results.append(element)
            
            result_elements = filtered_results
            total_found = len(result_elements)
            
            logger.info(f"Toplam {total_found} gerçek mevzuat sonucu bulundu")
            
            # Sayfalama hesaplama
            start_index = (page - 1) * per_page
            end_index = start_index + per_page
            paginated_elements = result_elements[start_index:end_index]
            
            # Her sonucu işle
            for index, element in enumerate(paginated_elements):
                try:
                    result_data = self._extract_result_data(element, index + start_index)
                    if result_data:
                        results.append(result_data)
                        logger.info(f"Mevzuat bulundu: {result_data['title'][:50]}...")
                except Exception as e:
                    logger.warning(f"Sonuç parse hatası {index}: {str(e)}")
                    continue
            
            return {
                'results': results,
                'total_count': total_found,
                'page': page,
                'per_page': per_page,
                'has_next': total_found > end_index,
                'has_previous': page > 1,
                'search_time': time.time(),
                'source': 'mevzuat.gov.tr'
            }
            
        except Exception as e:
            logger.error(f"Sonuç parse hatası: {str(e)}")
            return {
                'results': [],
                'total_count': 0,
                'page': page,
                'per_page': per_page,
                'has_next': False,
                'has_previous': False,
                'error': str(e)
            }
    
    def _extract_result_data(self, element, index):
        """Tek bir sonuç için veri çıkar - İyileştirilmiş"""
        try:
            # Mevzuat linkini bul
            mevzuat_link = element.find('a', href=re.compile(r'(MevzuatMetin|mevzuat.*No=)', re.I))
            
            if not mevzuat_link:
                # Fallback: herhangi bir link
                mevzuat_link = element.find('a')
            
            if not mevzuat_link:
                return None
            
            # Başlığı al - en uzun ve anlamlı metni bul
            title_candidates = []
            
            # Link kendi metnini kontrol et
            link_text = mevzuat_link.get_text(strip=True)
            if len(link_text) > 15:
                title_candidates.append(link_text)
            
            # Element içindeki diğer metinleri kontrol et
            for text_elem in element.find_all(['td', 'div', 'span'], string=True):
                text = text_elem.strip()
                if (len(text) > 20 and 
                    len(text) < 500 and
                    ('kanun' in text.lower() or 'yönetmelik' in text.lower() or 
                     'kararname' in text.lower() or 'tüzük' in text.lower() or
                     'genelge' in text.lower() or 'tebliğ' in text.lower())):
                    title_candidates.append(text)
            
            # En iyi başlığı seç
            if title_candidates:
                title = max(title_candidates, key=len)
            else:
                title = link_text if link_text else f"Mevzuat {index + 1}"
            
            # Başlığı temizle
            title = re.sub(r'^[-\s]*', '', title)  # Başlangıçtaki tireler
            title = re.sub(r'[.\s]*$', '', title)  # Sondaki noktalar
            title = ' '.join(title.split())  # Çoklu boşlukları temizle
            
            # URL'yi al ve düzelt
            url = mevzuat_link.get('href', '')
            if url and not url.startswith('http'):
                if url.startswith('/'):
                    url = f"https://www.mevzuat.gov.tr{url}"
                else:
                    url = f"https://www.mevzuat.gov.tr/{url}"
            
            # Mevzuat numarasını çıkar - daha gelişmiş
            mevzuat_no = ""
            text_content = element.get_text()
            
            # URL'den numara çıkarmayı dene
            if url:
                url_no_match = re.search(r'No=(\d+)', url, re.I)
                if url_no_match:
                    mevzuat_no = url_no_match.group(1)
            
            # Metin içinden numara çıkarmayı dene
            if not mevzuat_no:
                no_patterns = [
                    r'(?:Kanun\s*)?No:?\s*(\d{4,6})',  # Kanun No: 1234
                    r'Sayı:?\s*(\d{4,6})',  # Sayı: 1234
                    r'(\d{4,6})\s*sayılı',  # 1234 sayılı
                    r'(\d{4,6})\s*numaralı',  # 1234 numaralı
                    r'RG\s*:\s*\d+[/.-]\d+[/.-]\d+\s*-\s*(\d+)',  # RG formatı
                    r'(\d{4,6})',  # Sadece 4-6 haneli sayı
                ]
                
                for pattern in no_patterns:
                    match = re.search(pattern, text_content, re.IGNORECASE)
                    if match:
                        potential_no = match.group(1)
                        # Tarih olmadığından emin ol
                        if not re.search(r'\d{1,2}[./]\d{1,2}[./]' + potential_no, text_content):
                            mevzuat_no = potential_no
                            break
            
            # Mevzuat türünü belirle - başlık ve içerik analizi
            mevzuat_type = "Mevzuat"
            title_lower = title.lower()
            content_lower = text_content.lower()
            
            # Türü daha akıllıca belirle
            type_patterns = [
                (r'kanun', 'Kanun'),
                (r'cumhurbaşkanlığı\s+kararnamesi|cbk', 'Cumhurbaşkanlığı Kararnamesi'),
                (r'yönetmelik', 'Yönetmelik'),
                (r'tüzük', 'Tüzük'),
                (r'genelge', 'Genelge'),
                (r'tebliğ', 'Tebliğ'),
                (r'karar', 'Karar'),
                (r'yönerge', 'Yönerge'),
                (r'protokol', 'Protokol'),
                (r'anlaşma', 'Anlaşma')
            ]
            
            for pattern, type_name in type_patterns:
                if re.search(pattern, title_lower) or re.search(pattern, content_lower):
                    mevzuat_type = type_name
                    break
            
            # Tarihleri çıkar - daha gelişmiş
            date_str = ""
            rg_date = ""
            rg_number = ""
            
            # Tarih formatları
            date_patterns = [
                r'(\d{1,2}[./]\d{1,2}[./]\d{4})',
                r'(\d{4}[./]\d{1,2}[./]\d{1,2})',
                r'(\d{1,2}\s+\w+\s+\d{4})'
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, text_content)
                if match and not date_str:
                    date_str = match.group(1)
                    break
            
            # RG bilgilerini çıkar
            rg_match = re.search(r'RG\s*:?\s*(\d{1,2}[./]\d{1,2}[./]\d{4})\s*-?\s*(\d+)', text_content, re.I)
            if rg_match:
                rg_date = rg_match.group(1)
                rg_number = rg_match.group(2)
            
            # ID oluştur
            if mevzuat_no:
                result_id = f"live_{mevzuat_no}"
            else:
                result_id = f"live_result_{index}"
            
            # Önizleme metni - sadece önemli kısımları al
            preview_lines = []
            for line in text_content.split('\n'):
                line = line.strip()
                if (len(line) > 15 and 
                    not any(skip_word in line.lower() for skip_word in ['menü', 'giriş', 'arama', 'copyright']) and
                    len(preview_lines) < 3):
                    preview_lines.append(line)
            
            preview_text = ' '.join(preview_lines)
            if len(preview_text) > 300:
                preview_text = preview_text[:300] + "..."
            
            return {
                'id': result_id,
                'title': title,
                'mevzuat_no': mevzuat_no,
                'type': mevzuat_type,
                'date': date_str,
                'rg_date': rg_date,
                'rg_number': rg_number,
                'preview_text': preview_text,
                'url': f'/external-mevzuat/{result_id}/',  # Kendi sistemimizde göstermek için
                'external_url': url,  # Orijinal URL
                'source': 'live_direct',
                'full_text_available': True,
                'is_external': True
            }
            
        except Exception as e:
            logger.error(f"Result extraction error: {str(e)}")
            return None
    
    def get_mevzuat_detail(self, result_id):
        """Belirli bir mevzuat için detay bilgi al"""
        try:
            # ID'den mevzuat numarasını çıkar
            if 'live_' in result_id:
                # Cache kontrolü
                cache_key = f"detail_{result_id}"
                cached_detail = cache.get(cache_key)
                if cached_detail:
                    return cached_detail
                
                # Detay bilgiyi mevzuat.gov.tr'den çek
                # Bu external_mevzuat_views.py'daki fetch_mevzuat_detail fonksiyonunu kullanabilir
                from .external_mevzuat_views import fetch_mevzuat_detail
                
                # ID'den mevzuat numarasını çıkar
                parts = result_id.split('_')
                if len(parts) >= 2 and parts[1].isdigit():
                    mevzuat_no = parts[1]
                    detail = fetch_mevzuat_detail(mevzuat_no)
                    if detail:
                        # Cache'e kaydet
                        cache.set(cache_key, detail, self.cache_timeout)
                        return detail
            
            return None
            
        except Exception as e:
            logger.error(f"Get detail error: {str(e)}")
            return None
    
    def clear_cache(self):
        """Cache'i temizle"""
        try:
            # Django cache pattern deletion
            cache.delete_pattern("direct_live_*")
            cache.delete_pattern("detail_live_*")
            return True
        except Exception as e:
            logger.error(f"Cache clear error: {str(e)}")
            return False