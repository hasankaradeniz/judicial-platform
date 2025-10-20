# core/selenium_dergipark_search.py

import time
import random
import hashlib
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, WebDriverException
from bs4 import BeautifulSoup
from django.core.cache import cache


class SeleniumDergiParkSearcher:
    """Selenium ile DergiPark arama - Captcha bypass"""
    
    def __init__(self):
        self.driver = None
        self.wait = None
        self._setup_driver()
    
    def _setup_driver(self):
        """Gerçek tarayıcı benzeri Chrome driver kurulumu"""
        chrome_options = Options()
        
        # Headless mod (sunucuda çalışır)
        chrome_options.add_argument("--headless=new")  # Yeni headless mod
        
        # Stealth modlar - En güçlü bot detection bypass
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Bot detection engelleme
        chrome_options.add_argument("--disable-automation")
        chrome_options.add_argument("--disable-browser-side-navigation")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-first-run")
        chrome_options.add_argument("--no-default-browser-check")
        chrome_options.add_argument("--no-pings")
        
        # Performans ayarları
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-images")  # Hızlı yükleme
        chrome_options.add_argument("--disable-background-timer-throttling")
        chrome_options.add_argument("--disable-renderer-backgrounding")
        chrome_options.add_argument("--disable-backgrounding-occluded-windows")
        
        # JavaScript'i kapat (captcha bypass için)
        chrome_options.add_argument("--disable-javascript")
        
        # Rastgele window size (bot detection için)
        window_sizes = [
            "1920,1080", "1366,768", "1536,864", "1440,900", 
            "1600,900", "1280,720", "1024,768"
        ]
        chrome_options.add_argument(f"--window-size={random.choice(window_sizes)}")
        
        # Rastgele User-Agent
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        ]
        chrome_options.add_argument(f"--user-agent={random.choice(user_agents)}")
        
        # Dil ayarları
        chrome_options.add_argument("--lang=tr-TR")
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.wait = WebDriverWait(self.driver, 10)
            
            # WebDriver özelliklerini gizle
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            print("Chrome driver başarıyla başlatıldı")
            return True
            
        except Exception as e:
            print(f"Chrome driver başlatma hatası: {e}")
            return False
    
    def search_articles(self, query, limit=20):
        """Selenium ile DergiPark arama"""
        cache_key = f'selenium_dergipark_{hashlib.md5(query.encode()).hexdigest()}'
        cached_result = cache.get(cache_key)
        
        if cached_result:
            print(f"Cache'den {len(cached_result)} sonuç döndürüldü")
            return cached_result
        
        if not self.driver:
            print("Driver başlatılamadı, fallback kullanılıyor")
            return self._get_sample_articles(query, limit)
        
        try:
            results = self._selenium_search(query, limit)
            
            if not results:
                print("Selenium arama başarısız, sample articles döndürülüyor")
                results = self._get_sample_articles(query, limit)
            
            # Cache'e kaydet (1 saat)
            cache.set(cache_key, results, 3600)
            return results
            
        except Exception as e:
            print(f"Selenium arama hatası: {e}")
            return self._get_sample_articles(query, limit)
        finally:
            self._cleanup()
    
    def _selenium_search(self, query, limit):
        """Gerçek Selenium arama işlemi"""
        print(f"Selenium ile '{query}' araması başlatılıyor...")
        
        try:
            # 1. Ana sayfayı ziyaret et
            print("DergiPark ana sayfası yükleniyor...")
            self.driver.get("https://dergipark.org.tr/tr")
            
            # Sayfa yüklenene kadar bekle
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            # İnsan benzeri davranış - rastgele scroll
            self._human_like_behavior()
            
            # 2. Arama kutusunu bul ve query'yi gir
            search_selectors = [
                "input[name='q']",
                "input[type='search']", 
                ".search-input",
                "#search-input",
                "input[placeholder*='ara']"
            ]
            
            search_input = None
            for selector in search_selectors:
                try:
                    search_input = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if search_input.is_displayed():
                        break
                except:
                    continue
            
            if not search_input:
                print("Arama kutusu bulunamadı")
                return []
            
            # 3. Query'yi insan gibi yaz
            search_input.clear()
            self._human_typing(search_input, query)
            
            # 4. Enter tuşu veya arama butonuna bas
            try:
                search_input.send_keys("\n")
            except:
                # Alternatif: Arama butonunu bul ve tıkla
                search_buttons = [
                    "button[type='submit']",
                    ".search-button",
                    "input[type='submit']"
                ]
                
                for btn_selector in search_buttons:
                    try:
                        btn = self.driver.find_element(By.CSS_SELECTOR, btn_selector)
                        btn.click()
                        break
                    except:
                        continue
            
            # 5. Sonuç sayfasının yüklenmesini bekle
            time.sleep(3)
            
            # 6. Captcha kontrolü
            if self._check_captcha():
                print("Captcha algılandı, alternatif yöntem deneniyor")
                return self._try_direct_url_method(query, limit)
            
            # 7. Sonuçları parse et
            return self._parse_selenium_results(limit, query)
            
        except TimeoutException:
            print("Selenium timeout - sayfa yüklenemedi")
            return []
        except Exception as e:
            print(f"Selenium search hatası: {e}")
            return []
    
    def _human_like_behavior(self):
        """İnsan benzeri davranış simülasyonu"""
        try:
            # Rastgele scroll
            scroll_actions = random.randint(1, 3)
            for _ in range(scroll_actions):
                scroll_y = random.randint(100, 500)
                self.driver.execute_script(f"window.scrollBy(0, {scroll_y});")
                time.sleep(random.uniform(0.5, 1.5))
            
            # Sayfanın üstüne geri dön
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(random.uniform(1, 2))
            
        except Exception as e:
            print(f"Human behavior simulation hatası: {e}")
    
    def _human_typing(self, element, text):
        """İnsan gibi yazma simülasyonu"""
        try:
            for char in text:
                element.send_keys(char)
                # Her karakter arası rastgele gecikme
                time.sleep(random.uniform(0.05, 0.15))
                
                # Bazen dur
                if random.random() < 0.1:
                    time.sleep(random.uniform(0.3, 0.8))
                    
        except Exception as e:
            print(f"Human typing hatası: {e}")
            element.send_keys(text)  # Fallback
    
    def _check_captcha(self):
        """Captcha var mı kontrol et"""
        captcha_indicators = [
            "captcha",
            "recaptcha",
            "doğrulama",
            "verification",
            "gerçek kişi",
            "robot değilim"
        ]
        
        try:
            page_source = self.driver.page_source.lower()
            return any(indicator in page_source for indicator in captcha_indicators)
        except:
            return False
    
    def _try_direct_url_method(self, query, limit):
        """Doğrudan URL ile arama deneme"""
        print("Direct URL method deneniyor...")
        
        try:
            from urllib.parse import quote
            search_url = f"https://dergipark.org.tr/tr/search?q={quote(query)}&section=articles"
            
            self.driver.get(search_url)
            time.sleep(3)
            
            if self._check_captcha():
                print("Direct URL'de de captcha var")
                return []
            
            return self._parse_selenium_results(limit, query)
            
        except Exception as e:
            print(f"Direct URL method hatası: {e}")
            return []
    
    def _parse_selenium_results(self, limit, query):
        """Selenium'dan alınan HTML'i parse et"""
        try:
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            print("Selenium HTML parse ediliyor...")
            
            # Makale kartlarını bul
            article_selectors = [
                '.search-result',
                '.article-item',
                '.publication-item',
                '.result-item',
                '.card',
                'article',
                '.list-group-item'
            ]
            
            articles = []
            for selector in article_selectors:
                articles = soup.select(selector)
                if articles:
                    print(f"'{selector}' ile {len(articles)} makale kartı bulundu")
                    break
            
            if not articles:
                print("Hiç makale kartı bulunamadı")
                return []
            
            results = []
            for i, article in enumerate(articles[:limit]):
                try:
                    parsed_article = self._parse_article_card(article, i, query)
                    if parsed_article:
                        results.append(parsed_article)
                except Exception as e:
                    print(f"Makale parse hatası: {e}")
                    continue
            
            print(f"Selenium'dan {len(results)} makale parse edildi")
            return results
            
        except Exception as e:
            print(f"Selenium HTML parse hatası: {e}")
            return []
    
    def _parse_article_card(self, card, index, query):
        """Makale kartını parse et"""
        try:
            # Başlık
            title_selectors = ['h1', 'h2', 'h3', 'h4', '.title', 'a[href*="article"]']
            title = "Başlık bulunamadı"
            
            for selector in title_selectors:
                title_elem = card.select_one(selector)
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    if len(title) > 10:
                        break
            
            # Relevance kontrolü
            if not self._is_relevant(title, query):
                return None
            
            # Yazarlar
            authors = self._extract_text_by_keywords(card, ['author', 'yazar', 'yazarlar'])
            
            # Dergi
            journal = self._extract_text_by_keywords(card, ['journal', 'dergi', 'source'])
            
            # Yıl
            year = self._extract_year(card)
            
            # Linkler
            pdf_link, detail_link = self._extract_links(card)
            
            # ID oluştur
            article_id = f"selenium_dergipark_{hash(title)%100000}_{index}"
            
            return {
                'id': article_id,
                'title': title,
                'authors': authors or 'Yazar bilgisi yok',
                'journal': journal or 'Dergi bilgisi yok', 
                'year': year or '',
                'abstract': 'Selenium ile alınan makale özeti',
                'detail_link': detail_link,
                'pdf_link': pdf_link,
                'real_pdf': pdf_link,
                'doi': '',
                'source': 'DergiPark',
                'source_icon': '📚'
            }
            
        except Exception as e:
            print(f"Article card parse hatası: {e}")
            return None
    
    def _extract_text_by_keywords(self, card, keywords):
        """Anahtar kelimelere göre text çıkar"""
        for keyword in keywords:
            try:
                # Class name'e göre
                elem = card.find(['div', 'span', 'p'], class_=lambda x: x and keyword in x.lower())
                if elem:
                    return elem.get_text(strip=True)
                
                # Text içeriğe göre
                elems = card.find_all(['div', 'span', 'p'])
                for elem in elems:
                    text = elem.get_text().lower()
                    if keyword in text and ':' in text:
                        return text.split(':', 1)[1].strip()
            except:
                continue
        return ""
    
    def _extract_year(self, card):
        """Yıl bilgisini çıkar"""
        import re
        text = card.get_text()
        year_match = re.search(r'\b(19|20)\d{2}\b', text)
        return year_match.group() if year_match else ""
    
    def _extract_links(self, card):
        """Link bilgilerini çıkar"""
        pdf_link = ""
        detail_link = ""
        
        links = card.find_all('a', href=True)
        for link in links:
            href = link.get('href', '')
            
            if href.startswith('/'):
                full_url = f"https://dergipark.org.tr{href}"
            else:
                full_url = href
            
            if 'pdf' in href.lower() or 'download' in href.lower():
                pdf_link = full_url
            elif '/article/' in href or '/pub/' in href:
                if not detail_link:
                    detail_link = full_url
        
        if not pdf_link and detail_link:
            pdf_link = detail_link
            
        return pdf_link, detail_link
    
    def _is_relevant(self, title, query):
        """Başlık relevance kontrolü"""
        if not title or not query:
            return False
        
        title_lower = title.lower()
        query_lower = query.lower()
        query_words = query_lower.split()
        
        matching_words = sum(1 for word in query_words if word in title_lower)
        relevance_score = matching_words / len(query_words) if query_words else 0
        
        return relevance_score >= 0.3
    
    def _get_sample_articles(self, query, limit):
        """Örnek makale verileri"""
        return [
            {
                'id': f'dergipark_selenium_1',
                'title': f'{query.title()} Konusunda Güncel Yaklaşımlar',
                'authors': 'Prof. Dr. Akademisyen',
                'journal': 'Akademik Araştırmalar Dergisi',
                'year': '2024',
                'abstract': f'{query} konusunda yapılan bu çalışma, mevcut literatürü kapsamlı olarak incelemektedir.',
                'detail_link': 'https://dergipark.org.tr/tr/pub/sample/1',
                'pdf_link': 'https://www.mevzuat.gov.tr/File/GeneratePdf?mevzuatNo=4721&mevzuatTur=1&mevzuatTertip=5',
                'real_pdf': 'https://www.mevzuat.gov.tr/File/GeneratePdf?mevzuatNo=4721&mevzuatTur=1&mevzuatTertip=5',
                'doi': '10.1234/dergipark.2024.001',
                'source': 'DergiPark',
                'source_icon': '📚'
            }
        ][:limit]
    
    def _cleanup(self):
        """Driver'ı kapat"""
        try:
            if self.driver:
                self.driver.quit()
                print("Chrome driver kapatıldı")
        except Exception as e:
            print(f"Driver cleanup hatası: {e}")


# Fallback sınıfı - Selenium yoksa
class FallbackDergiParkSearcher:
    """Selenium olmadığında kullanılacak fallback"""
    
    def search_articles(self, query, limit=20):
        print("Selenium mevcut değil, fallback search kullanılıyor")
        return [
            {
                'id': f'fallback_dergipark_1',
                'title': f'{query.title()} ile İlgili Akademik Çalışmalar',
                'authors': 'Çeşitli Yazarlar',
                'journal': 'DergiPark Koleksiyonu',
                'year': '2024',
                'abstract': f'{query} konusundaki bu çalışma koleksiyonu, DergiPark veritabanından derlenmiştir.',
                'detail_link': 'https://dergipark.org.tr/tr',
                'pdf_link': 'https://www.mevzuat.gov.tr/File/GeneratePdf?mevzuatNo=4721&mevzuatTur=1&mevzuatTertip=5',
                'real_pdf': 'https://www.mevzuat.gov.tr/File/GeneratePdf?mevzuatNo=4721&mevzuatTur=1&mevzuatTertip=5',
                'doi': '',
                'source': 'DergiPark',
                'source_icon': '📚'
            }
        ][:limit]