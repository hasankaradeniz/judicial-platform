# core/simple_mevzuat_search.py

import time
import re
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from django.core.cache import cache
import logging
import urllib.parse

logger = logging.getLogger(__name__)

class SimpleMevzuatSearcher:
    """Basit ve etkili mevzuat.gov.tr arama sistemi"""
    
    def __init__(self):
        self.base_url = "https://www.mevzuat.gov.tr"
        
    def search_legislation(self, query, mevzuat_type=None, page=1, per_page=20):
        """Ana arama fonksiyonu - basit ve etkili"""
        try:
            # Cache kontrolü
            cache_key = f"simple_search_{query}_{mevzuat_type}_{page}".replace(' ', '_')
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.info(f"Cache'den sonuç: {query}")
                return cached_result
            
            # İlk olarak Requests ile deneme
            results = self._try_requests_search(query, mevzuat_type, page, per_page)
            
            # Eğer sadece "Kanunlar Fihristi" gibi navigation sonuçları varsa Selenium'u dene
            if (not results or results['total_count'] == 0 or 
                (results['results'] and all('fihristi' in r['title'].lower() for r in results['results']))):
                logger.info("Requests yetersiz sonuç, Selenium deneniyor...")
                results = self._try_selenium_search(query, mevzuat_type, page, per_page)
            
            # Cache'e kaydet
            if results and results['total_count'] > 0:
                cache.set(cache_key, results, 1800)  # 30 dakika
                
            return results
            
        except Exception as e:
            logger.error(f"Search error: {str(e)}")
            return {
                'results': [],
                'total_count': 0,
                'page': page,
                'per_page': per_page,
                'has_next': False,
                'has_previous': False,
                'error': str(e)
            }
    
    def _try_requests_search(self, query, mevzuat_type, page, per_page):
        """Requests ile POST arama deneme"""
        try:
            # Doğru arama URL'si ve method
            search_url = "https://www.mevzuat.gov.tr/aramasonuc"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Content-Type': 'application/x-www-form-urlencoded',
                'Referer': 'https://www.mevzuat.gov.tr/',
                'Origin': 'https://www.mevzuat.gov.tr'
            }
            
            # Önce ana sayfayı ziyaret et (session için)
            session = requests.Session()
            session.headers.update(headers)
            
            logger.info("Ana sayfa ziyaret ediliyor...")
            main_page = session.get("https://www.mevzuat.gov.tr/", timeout=15)
            
            if main_page.status_code == 200:
                # Anti-forgery token'ı bul
                soup = BeautifulSoup(main_page.content, 'html.parser')
                antiforgery_input = soup.find('input', {'name': 'antiforgerytoken'})
                antiforgery_token = antiforgery_input.get('value', '') if antiforgery_input else ''
                
                logger.info(f"Antiforgery token: {antiforgery_token[:20]}...")
                
                # POST verisi hazırla
                post_data = {
                    'AranacakMetin': query,
                    'antiforgerytoken': antiforgery_token
                }
                
                logger.info(f"POST arama yapılıyor: {search_url}")
                logger.info(f"Arama terimi: {query}")
                
                # POST isteği gönder
                response = session.post(search_url, data=post_data, timeout=20)
                
                if response.status_code == 200:
                    logger.info("POST arama başarılı, HTML parse ediliyor...")
                    results = self._parse_html_content(response.text, page, per_page)
                    
                    if results and results['total_count'] > 0:
                        logger.info(f"POST arama sonucu: {results['total_count']} sonuç")
                        return results
                    else:
                        logger.warning("POST arama sonuç vermedi")
                else:
                    logger.error(f"POST arama HTTP hatası: {response.status_code}")
            
            return None
            
        except Exception as e:
            logger.error(f"Requests search error: {str(e)}")
            return None
    
    def _try_selenium_search(self, query, mevzuat_type, page, per_page):
        """Selenium ile tam arama deneyimi - JavaScript sonuçlarını bekle"""
        driver = None
        try:
            # Chrome ayarları
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            
            # Driver oluştur
            try:
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=chrome_options)
            except:
                driver = webdriver.Chrome(options=chrome_options)
            
            driver.set_page_load_timeout(30)
            
            # Ana sayfaya git
            logger.info("Selenium ile ana sayfa yükleniyor...")
            driver.get("https://www.mevzuat.gov.tr")
            time.sleep(3)
            
            # AranacakMetin input'unu bul ve arama yap
            try:
                search_input = driver.find_element(By.NAME, "AranacakMetin")
                logger.info("Arama kutusu bulundu")
                
                # Arama terimini gir
                search_input.clear()
                search_input.send_keys(query)
                logger.info(f"Arama terimi girildi: {query}")
                
                # Form submit et
                search_input.submit()
                logger.info("Form submit edildi")
                
                # Arama sonuç sayfasının yüklenmesini bekle
                time.sleep(5)
                
                current_url = driver.current_url
                logger.info(f"Yönlendirilen URL: {current_url}")
                
                # JavaScript sonuçlarının yüklenmesini bekle
                max_wait = 30
                wait_time = 0
                
                while wait_time < max_wait:
                    # Başlık sekmesindeki sonuçları kontrol et
                    try:
                        baslik_body = driver.find_element(By.ID, "Baslik_body")
                        if not baslik_body.get_attribute("class") or "d-none" not in baslik_body.get_attribute("class"):
                            # Sonuçlar yüklenmiş
                            logger.info("Başlık sonuçları yüklendi")
                            break
                    except:
                        pass
                    
                    # Tablolara bak
                    tables = driver.find_elements(By.TAG_NAME, "table")
                    if tables:
                        # En az bir tablo varsa sonuçlar yüklenmiş olabilir
                        logger.info(f"{len(tables)} tablo bulundu")
                        break
                    
                    time.sleep(2)
                    wait_time += 2
                    logger.info(f"JavaScript sonuçları bekleniyor... ({wait_time}s)")
                
                # "Başlık" tabını aktif et - arama sonuçları için
                try:
                    baslik_tab = driver.find_element(By.ID, "nav-Baslik-tab")
                    baslik_tab.click()
                    time.sleep(3)
                    logger.info("Başlık tabı aktif edildi")
                except Exception as e:
                    logger.warning(f"Başlık tabı aktif edilemedi: {str(e)}")
                
                # Sayfa başına gösterilecek sonuç sayısını maksimuma çıkar
                try:
                    # JavaScript ile DataTable'ı 100 sonuç gösterecek şekilde ayarla
                    driver.execute_script("""
                        try {
                            // Baslik_Datatable'ın page length'ini 100 yap
                            if (window.jQuery && window.jQuery.fn.DataTable) {
                                var table = jQuery('#Baslik_Datatable').DataTable();
                                if (table) {
                                    table.page.len(100).draw();
                                    console.log('DataTable page length set to 100');
                                }
                            }
                        } catch(e) {
                            console.log('Error setting DataTable page length: ' + e);
                        }
                    """)
                    
                    logger.info("JavaScript ile sayfa başına 100 sonuç ayarlandı")
                    time.sleep(3)  # Tablonun yeniden yüklenmesini bekle
                    
                    # Tablonun güncellenmesini bekle
                    table_loaded = False
                    for i in range(10):
                        try:
                            # Sayfa bilgisini kontrol et
                            info_element = driver.find_element(By.ID, "Baslik_Datatable_info")
                            info_text = info_element.text
                            logger.info(f"Tablo durumu: {info_text}")
                            
                            # Eğer 100 sonuç yüklendiyse veya daha fazla sonuç varsa
                            if "100" in info_text or ("272" in info_text and ("100" in info_text or "272" in info_text)):
                                table_loaded = True
                                break
                        except:
                            pass
                        time.sleep(1)
                    
                    if table_loaded:
                        logger.info("Tablo 100 sonuçla güncellendi")
                    else:
                        logger.warning("Tablo 100 sonuçla güncellenemedi, normal sayfalama ile devam ediliyor")
                    
                except Exception as e:
                    logger.warning(f"Sayfa başına sonuç sayısı ayarlanamadı: {str(e)}")
                
                # Tüm sayfaları topla
                all_results = []
                current_page = 1
                max_pages = 50  # Güvenlik için maksimum sayfa sınırı
                
                while current_page <= max_pages:
                    try:
                        logger.info(f"Sayfa {current_page} işleniyor...")
                        
                        # Mevcut sayfanın sonuçlarını al
                        html_content = driver.page_source
                        page_results = self._parse_selenium_content(html_content, current_page, 100)
                        
                        if page_results and page_results['results']:
                            all_results.extend(page_results['results'])
                            logger.info(f"Sayfa {current_page}: {len(page_results['results'])} sonuç eklendi (Toplam: {len(all_results)})")
                            
                            # Sonraki sayfa var mı kontrol et
                            try:
                                # Her defasında yeni element bul (stale element reference'dan kaçınmak için)
                                next_button = driver.find_element(By.ID, "Baslik_Datatable_next")
                                next_button_class = next_button.get_attribute("class") or ""
                                
                                logger.info(f"Next button class: {next_button_class}")
                                
                                if "disabled" in next_button_class:
                                    logger.info("Son sayfaya ulaşıldı")
                                    break
                                else:
                                    # Sonraki sayfaya git
                                    logger.info("Sonraki sayfaya geçiliyor...")
                                    
                                    # JavaScript ile DataTable'ın next page fonksiyonunu kullan
                                    try:
                                        driver.execute_script("""
                                            try {
                                                if (window.jQuery && window.jQuery.fn.DataTable) {
                                                    var table = jQuery('#Baslik_Datatable').DataTable();
                                                    if (table) {
                                                        table.page('next').draw(false);
                                                        console.log('DataTable next page called');
                                                    }
                                                }
                                            } catch(e) {
                                                console.log('Error calling DataTable next: ' + e);
                                                // Fallback to clicking the button
                                                document.getElementById('Baslik_Datatable_next').click();
                                            }
                                        """)
                                        logger.info("Next page JavaScript ile çağrıldı")
                                    except Exception as e:
                                        logger.warning(f"JavaScript next page hatası: {str(e)}")
                                        # Fallback to normal click
                                        next_button.click()
                                        logger.info("Next button normal tıklandı")
                                    
                                    # Sayfanın yüklenmesini bekle
                                    time.sleep(5)
                                    
                                    # Yeni sayfa yüklendiğini kontrol et
                                    page_wait = 0
                                    while page_wait < 15:
                                        try:
                                            # Sayfa numarasının değiştiğini kontrol et
                                            active_page = driver.find_element(By.CSS_SELECTOR, ".pagination .page-item.active .page-link")
                                            active_page_num = int(active_page.text.strip())
                                            if active_page_num == current_page + 1:
                                                logger.info(f"Sayfa {current_page + 1} yüklendi")
                                                break
                                        except Exception as e:
                                            logger.debug(f"Sayfa kontrol hatası: {str(e)}")
                                            pass
                                        time.sleep(1)
                                        page_wait += 1
                                    
                                    current_page += 1
                            except Exception as e:
                                logger.warning(f"Sonraki sayfa bulunamadı: {str(e)}")
                                break
                        else:
                            logger.warning(f"Sayfa {current_page}'da sonuç bulunamadı")
                            break
                            
                    except Exception as e:
                        logger.error(f"Sayfa {current_page} işlenirken hata: {str(e)}")
                        break
                
                # Son hali ile sayfayı parse et
                html_content = driver.page_source
                
                # HTML içeriğini filtrele - sadece ana içerik bölümünü al
                filtered_html = self._filter_content_html(html_content)
                
                # HTML dosyasına kaydet (debug için)
                with open('/tmp/selenium_search_result.html', 'w', encoding='utf-8') as f:
                    f.write(filtered_html)
                logger.info("Filtrelenmiş Selenium HTML kaydedildi: /tmp/selenium_search_result.html")
                
                # Toplam sonuç sayısını belirle
                total_results = len(all_results)
                logger.info(f"Toplam {total_results} sonuç toplandı")
                
                # Tüm sonuçları tek sayfada döndür
                if all_results:
                    return {
                        'results': all_results,
                        'total_count': total_results,
                        'page': 1,  # Tek sayfa
                        'per_page': total_results,  # Tüm sonuçlar
                        'has_next': False,
                        'has_previous': False,
                        'source': 'selenium_mevzuat.gov.tr_all'
                    }
                else:
                    logger.warning("Selenium arama sonuç vermedi")
                
            except Exception as e:
                logger.error(f"Selenium arama hatası: {str(e)}")
            
            return {
                'results': [],
                'total_count': 0,
                'page': page,
                'per_page': per_page,
                'has_next': False,
                'has_previous': False
            }
            
        except Exception as e:
            logger.error(f"Selenium search error: {str(e)}")
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
    
    def _parse_html_content(self, html_content, page, per_page):
        """HTML içeriğini parse et ve mevzuat sonuçlarını bul"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            results = []
            
            logger.info("HTML parse ediliyor...")
            
            # Debug: Sayfada 'mevzuat' kelimesini ara
            page_text = soup.get_text().lower()
            if 'mevzuat' not in page_text:
                logger.warning("Sayfada 'mevzuat' kelimesi bulunamadı")
            
            # Farklı yapıları dene
            found_results = []
            
            # 1. Tablo satırlarını ara
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    links = row.find_all('a', href=True)
                    for link in links:
                        href = link.get('href', '')
                        text = link.get_text(strip=True)
                        
                        # Mevzuat linki kontrolü
                        if (('MevzuatMetin' in href or 'mevzuat' in href.lower()) and
                            len(text) > 10 and
                            any(keyword in text.lower() for keyword in ['kanun', 'yönetmelik', 'tüzük', 'kararname', 'genelge', 'tebliğ'])):
                            found_results.append({
                                'element': row,
                                'link': link,
                                'href': href,
                                'text': text
                            })
            
            # 2. Div elementlerini ara
            if not found_results:
                divs = soup.find_all('div')
                for div in divs:
                    links = div.find_all('a', href=True)
                    for link in links:
                        href = link.get('href', '')
                        text = link.get_text(strip=True)
                        
                        if (('MevzuatMetin' in href or 'mevzuat' in href.lower()) and
                            len(text) > 10 and
                            any(keyword in text.lower() for keyword in ['kanun', 'yönetmelik', 'tüzük', 'kararname', 'genelge', 'tebliğ'])):
                            found_results.append({
                                'element': div,
                                'link': link,
                                'href': href,
                                'text': text
                            })
            
            # 3. Tüm mevzuat linklerini ara (son çare)
            if not found_results:
                all_links = soup.find_all('a', href=True)
                for link in all_links:
                    href = link.get('href', '')
                    text = link.get_text(strip=True)
                    
                    if (('MevzuatMetin' in href or 'mevzuat' in href.lower()) and
                        len(text) > 10):
                        found_results.append({
                            'element': link.parent,
                            'link': link,
                            'href': href,
                            'text': text
                        })
            
            logger.info(f"Toplam {len(found_results)} potansiyel sonuç bulundu")
            
            # Sonuçları temizle ve formatla
            for i, result in enumerate(found_results):
                try:
                    formatted_result = self._format_result(result, i)
                    if formatted_result:
                        results.append(formatted_result)
                except Exception as e:
                    logger.warning(f"Sonuç formatlaması hatası {i}: {str(e)}")
                    continue
            
            # Debug çıktısı
            if results:
                logger.info(f"Formatlanmış {len(results)} sonuç:")
                for r in results[:3]:  # İlk 3 sonucu logla
                    logger.info(f"- {r['title'][:50]}...")
            else:
                logger.warning("Hiç formatlanmış sonuç bulunamadı")
                # HTML'in bir bölümünü logla
                logger.debug(f"HTML snippet: {str(soup)[:500]}...")
            
            # Sayfalama
            total_found = len(results)
            start_index = (page - 1) * per_page
            end_index = start_index + per_page
            paginated_results = results[start_index:end_index]
            
            return {
                'results': paginated_results,
                'total_count': total_found,
                'page': page,
                'per_page': per_page,
                'has_next': total_found > end_index,
                'has_previous': page > 1,
                'source': 'mevzuat.gov.tr'
            }
            
        except Exception as e:
            logger.error(f"HTML parse error: {str(e)}")
            return {
                'results': [],
                'total_count': 0,
                'page': page,
                'per_page': per_page,
                'has_next': False,
                'has_previous': False,
                'error': str(e)
            }
    
    def _format_result(self, result_data, index):
        """Sonucu formatla"""
        try:
            link = result_data['link']
            element = result_data['element']
            href = result_data['href']
            title = result_data['text']
            
            # URL'yi düzelt
            if href.startswith('/'):
                full_url = f"https://www.mevzuat.gov.tr{href}"
            elif not href.startswith('http'):
                full_url = f"https://www.mevzuat.gov.tr/{href}"
            else:
                full_url = href
            
            # Mevzuat numarasını çıkar
            mevzuat_no = ""
            
            # URL'den numara çıkarmayı dene
            url_match = re.search(r'No=(\d+)', href, re.I)
            if url_match:
                mevzuat_no = url_match.group(1)
            
            # Başlıktan numara çıkarmayı dene
            if not mevzuat_no:
                title_match = re.search(r'(\d{4,6})', title)
                if title_match:
                    mevzuat_no = title_match.group(1)
            
            # Element içerisinden daha fazla bilgi çıkar
            element_text = element.get_text() if element else title
            
            # Tür belirleme
            mevzuat_type = "Mevzuat"
            title_lower = title.lower()
            
            if 'kanun' in title_lower:
                mevzuat_type = "Kanun"
            elif 'yönetmelik' in title_lower:
                mevzuat_type = "Yönetmelik"
            elif 'kararname' in title_lower:
                mevzuat_type = "Cumhurbaşkanlığı Kararnamesi"
            elif 'tüzük' in title_lower:
                mevzuat_type = "Tüzük"
            elif 'genelge' in title_lower:
                mevzuat_type = "Genelge"
            elif 'tebliğ' in title_lower:
                mevzuat_type = "Tebliğ"
            
            # Tarih çıkar
            date_match = re.search(r'(\d{1,2}[./]\d{1,2}[./]\d{4})', element_text)
            date_str = date_match.group(1) if date_match else ""
            
            # ID oluştur
            result_id = f"live_{mevzuat_no}" if mevzuat_no else f"live_result_{index}"
            
            # Önizleme metni
            preview = element_text[:200].strip() + "..." if len(element_text) > 200 else element_text.strip()
            
            return {
                'id': result_id,
                'title': title.strip(),
                'mevzuat_no': mevzuat_no,
                'type': mevzuat_type,
                'date': date_str,
                'rg_date': '',
                'rg_number': '',
                'preview_text': preview,
                'url': f'/external-mevzuat/{result_id}/',
                'external_url': full_url,
                'source': 'live_direct',
                'full_text_available': True,
                'is_external': True
            }
            
        except Exception as e:
            logger.error(f"Result formatting error: {str(e)}")
            return None
    
    def _filter_content_html(self, html_content):
        """HTML içeriğini filtrele - header ve navigation bölümlerini kaldır - Güçlendirilmiş"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Kaldırılacak elementler - genişletilmiş liste
            elements_to_remove = [
                # Header ve navigation
                'nav', 'navbar', 'header',
                # İstenmeyen div'ler - daha spesifik
                {'div': {'id': 'navContainer'}},
                {'div': {'class': 'navbar'}},
                {'div': {'class': 'container pr-0 mt-2 mb-1'}},
                {'div': {'class': 'navbar-nav'}},
                {'div': {'class': 'dropdown'}},
                {'div': {'class': 'modal'}},
                {'div': {'id': 'loaderContainer'}},
                # Logo ve marka elementleri
                {'div': {'id': 'text-logo-container'}},
                {'img': {'id': 'logo-img'}},
                {'a': {'id': 'text-logo'}},
                # Navigation menüler
                {'ul': {'class': 'navbar-nav'}},
                {'li': {'class': 'nav-item'}},
                # Footer
                'footer',
                # Script'ler ve style'lar
                'script', 'style',
                # Meta taglar
                'meta', 'link'
            ]
            
            for element_selector in elements_to_remove:
                if isinstance(element_selector, str):
                    # Tag name
                    for element in soup.find_all(element_selector):
                        element.decompose()
                elif isinstance(element_selector, dict):
                    # Tag with attributes
                    for tag, attrs in element_selector.items():
                        for element in soup.find_all(tag, attrs):
                            element.decompose()
            
            # Header metin içeriğini de temizle
            header_text_patterns = [
                'T.C. CUMHURBAŞKANLIĞI',
                'MEVZUAT BİLGİ SİSTEMİ',
                'Mevzuat Türü',
                'Kanunlar',
                'Yönetmelikler',
                'Tebliğler',
                'Oturum Aç',
                'Favorilerim'
            ]
            
            # Text içeriklerini kontrol et ve header olanları kaldır
            all_elements = soup.find_all(text=True)
            for element in all_elements:
                if isinstance(element, str) and element.strip():
                    text_upper = element.strip().upper()
                    if any(pattern.upper() in text_upper for pattern in header_text_patterns):
                        if element.parent:
                            element.parent.decompose()
            
            # Sadece ana içerik bölümünü tut
            content_container = soup.find('div', {'class': 'container-fluid icerik content-wrapper'})
            if content_container:
                # İçerik container'ından da gereksiz navigation elementlerini temizle
                nav_elements = content_container.find_all(['nav', 'ul'], class_=['nav', 'navbar-nav'])
                for nav_el in nav_elements:
                    nav_el.decompose()
                
                # Tab navigation'ı da temizle - ama içeriği koru
                tab_nav = content_container.find('nav', class_='mt-4')
                if tab_nav:
                    tab_nav.decompose()
                
                # Minimal HTML structure oluştur
                filtered_html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="utf-8">
                    <title>Mevzuat Arama Sonuçları - Sadece İçerik</title>
                </head>
                <body>
                    {content_container}
                </body>
                </html>
                """
                logger.info("HTML içerik filtrelendi - header/nav elementleri temizlendi")
                return filtered_html
            else:
                # İçerik bölümü bulunamazsa, daha agresif temizlik yap
                logger.warning("Ana içerik bölümü bulunamadı, agresif filtreleme yapılıyor")
                
                # Tüm header/nav elementlerini kaldır
                for tag in ['nav', 'header', 'aside', 'footer']:
                    for element in soup.find_all(tag):
                        element.decompose()
                
                # ID'si nav, menu, header içeren divleri kaldır
                for div in soup.find_all('div'):
                    div_id = div.get('id', '').lower()
                    div_class = ' '.join(div.get('class', [])).lower()
                    
                    if any(keyword in div_id for keyword in ['nav', 'menu', 'header', 'footer', 'modal']):
                        div.decompose()
                    elif any(keyword in div_class for keyword in ['navbar', 'navigation', 'header', 'footer', 'modal']):
                        div.decompose()
                
                return str(soup)
                
        except Exception as e:
            logger.error(f"HTML filtreleme hatası: {str(e)}")
            return html_content
    
    def _parse_selenium_content(self, html_content, page, per_page):
        """Selenium ile alınan HTML'i özel olarak parse et"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            results = []
            total_count = 0
            
            logger.info("Selenium HTML parse ediliyor...")
            
            # Toplam sonuç sayısını dataTables_info'dan çıkar - farklı tablolardan dene
            info_divs = ['Baslik_Datatable_info', 'Tumu_Datatable_info', 'Icerik_Datatable_info']
            
            for info_id in info_divs:
                info_div = soup.find('div', {'id': info_id})
                if info_div:
                    info_text = info_div.get_text()
                    # "272 Kayıttan 1 - 10 Arası Kayıtlar" formatından toplam sayıyı çıkar
                    total_match = re.search(r'(\d+)\s+Kayıttan', info_text)
                    if total_match:
                        total_count = int(total_match.group(1))
                        logger.info(f"Toplam sonuç sayısı ({info_id}): {total_count}")
                        break
            
            # Dinamik yüklenen tab içeriklerini kontrol et - öncelik "Baslik" tabında
            tab_bodies = ['Baslik_body', 'Tumu_body', 'Icerik_body']
            
            for tab_id in tab_bodies:
                logger.info(f"Tab kontrol ediliyor: {tab_id}")
                tab_element = soup.find('div', {'id': tab_id})
                
                if tab_element and 'd-none' not in str(tab_element.get('class', [])):
                    # Bu tab aktif ve içeriği var
                    logger.info(f"Aktif tab bulundu: {tab_id}")
                    
                    # Tab içerisindeki tabloları bul
                    tables = tab_element.find_all('table')
                    for table in tables:
                        rows = table.find_all('tr')
                        logger.info(f"Tablo {len(rows)} satır içeriyor")
                        
                        for row in rows[1:]:  # Header'ı atla
                            cells = row.find_all(['td', 'th'])
                            if len(cells) >= 2:  # En az 2 hücre olmalı
                                # İlk hücrede mevzuat numarası, ikinci hücrede başlık
                                mevzuat_no_cell = cells[0]
                                title_cell = cells[1] if len(cells) > 1 else cells[0]
                                
                                # Mevzuat numarası
                                mevzuat_no = ""
                                no_link = mevzuat_no_cell.find('a', href=True)
                                if no_link:
                                    mevzuat_no = no_link.get_text(strip=True)
                                
                                # Başlık ve link
                                title_link = title_cell.find('a', href=True)
                                if title_link:
                                    href = title_link.get('href', '')
                                    
                                    # Başlık div'ini bul
                                    title_div = title_link.find('div')
                                    if title_div:
                                        # Highlight span'ını temizle
                                        for span in title_div.find_all('span'):
                                            span.unwrap()
                                        title = title_div.get_text(strip=True)
                                    else:
                                        title = title_link.get_text(strip=True)
                                    
                                    if title and len(title) > 5:
                                        logger.info(f"Sonuç bulundu: {title[:50]}...")
                                        
                                        # URL'yi düzelt
                                        if href.startswith('/'):
                                            full_url = f"https://www.mevzuat.gov.tr/{href}"
                                        elif not href.startswith('http'):
                                            full_url = f"https://www.mevzuat.gov.tr/{href}"
                                        else:
                                            full_url = href
                                        
                                        # Detay bilgilerini çıkar
                                        detail_div = title_link.find('div', class_='mt-1')
                                        rg_date = ""
                                        rg_number = ""
                                        mevzuat_type = "Mevzuat"
                                        
                                        if detail_div:
                                            detail_text = detail_div.get_text()
                                            
                                            # Mevzuat türü
                                            if 'Kanunlar' in detail_text:
                                                mevzuat_type = "Kanun"
                                            elif 'Yönetmelik' in detail_text:
                                                mevzuat_type = "Yönetmelik"
                                            elif 'Tüzük' in detail_text:
                                                mevzuat_type = "Tüzük"
                                            elif 'Kararname' in detail_text:
                                                mevzuat_type = "Cumhurbaşkanlığı Kararnamesi"
                                            
                                            # Resmi Gazete tarihi
                                            rg_date_match = re.search(r'Resmî Gazete Tarihi:\s*</b></i>\s*(\d{2}\.\d{2}\.\d{4})', detail_text)
                                            if rg_date_match:
                                                rg_date = rg_date_match.group(1)
                                            
                                            # Resmi Gazete sayısı
                                            rg_number_match = re.search(r'Sayısı:\s*</b></i>\s*(\d+)', detail_text)
                                            if rg_number_match:
                                                rg_number = rg_number_match.group(1)
                                        
                                        # URL'den mevzuat parametrelerini çıkar
                                        if not mevzuat_no:
                                            url_match = re.search(r'MevzuatNo=(\d+)', href, re.I)
                                            if url_match:
                                                mevzuat_no = url_match.group(1)
                                        
                                        result_id = f"live_{mevzuat_no}" if mevzuat_no else f"live_result_{len(results)}"
                                        
                                        # Önizleme metni oluştur
                                        preview_parts = []
                                        if mevzuat_type != "Mevzuat":
                                            preview_parts.append(mevzuat_type)
                                        if rg_date:
                                            preview_parts.append(f"RG: {rg_date}")
                                        if rg_number:
                                            preview_parts.append(f"Sayı: {rg_number}")
                                        
                                        preview_text = " | ".join(preview_parts) if preview_parts else title[:100]
                                        
                                        formatted_result = {
                                            'id': result_id,
                                            'title': title.strip(),
                                            'mevzuat_no': mevzuat_no,
                                            'type': mevzuat_type,
                                            'date': rg_date,
                                            'rg_date': rg_date,
                                            'rg_number': rg_number,
                                            'preview_text': preview_text,
                                            'url': f'/external-mevzuat/{result_id}/',
                                            'external_url': full_url,
                                            'source': 'live_selenium',
                                            'full_text_available': True,
                                            'is_external': True
                                        }
                                        
                                        results.append(formatted_result)
            
            # Eğer tab'larda sonuç yoksa, genel HTML'de ara
            if not results:
                logger.info("Tab'larda sonuç bulunamadı, genel HTML'de aranıyor...")
                results = self._parse_html_content(html_content, page, per_page)['results']
            
            logger.info(f"Selenium parsing tamamlandı: {len(results)} sonuç")
            
            # Eğer toplam count belirlenemediyse, bulunan sonuç sayısını kullan
            if total_count == 0:
                total_count = len(results)
            
            # Sayfalama - gerçek toplam sonuç sayısını kullan
            # DataTables'dan gelen sonuçlar zaten sayfalanmış (10'ar)
            # Sadece o sayfaya ait sonuçları döndür
            return {
                'results': results,  # DataTables'dan gelen sonuçlar zaten sayfalanmış
                'total_count': total_count,
                'page': page,
                'per_page': per_page,
                'has_next': page * per_page < total_count,
                'has_previous': page > 1,
                'source': 'selenium_mevzuat.gov.tr'
            }
            
        except Exception as e:
            logger.error(f"Selenium HTML parse error: {str(e)}")
            return {
                'results': [],
                'total_count': 0,
                'page': page,
                'per_page': per_page,
                'has_next': False,
                'has_previous': False,
                'error': str(e)
            }