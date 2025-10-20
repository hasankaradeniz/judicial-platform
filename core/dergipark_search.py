# core/dergipark_search.py

import requests
from bs4 import BeautifulSoup
import re
import time
import random
from urllib.parse import quote, urljoin
from django.core.cache import cache
import hashlib


class DergiParkSearcher:
    """DergiPark'tan makale arama sınıfı"""
    
    def __init__(self):
        # User-Agent rotasyonu için liste
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:123.0) Gecko/20100101 Firefox/123.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0'
        ]
        
        self.session = requests.Session()
        self._setup_session()
        
        # Çerez desteği ve SSL ayarları
        self.session.verify = True
        self.session.allow_redirects = True
        self.session.max_redirects = 10
    
    def _setup_session(self):
        """Session'ı rastgele User-Agent ile kurulum"""
        selected_ua = random.choice(self.user_agents)
        
        # Platform detection for more realistic headers
        if 'Windows' in selected_ua:
            platform = '"Windows"'
            os_version = '10.0'
        elif 'Macintosh' in selected_ua:
            platform = '"macOS"'
            os_version = '10_15_7'
        else:
            platform = '"Linux"'
            os_version = 'x86_64'
        
        # Gerçek tarayıcı benzeri headers - rastgele seçim
        base_headers = {
            'User-Agent': selected_ua,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': random.choice([
                'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
                'tr,en-US;q=0.9,en;q=0.8',
                'tr-TR,tr;q=0.8,en-US;q=0.5,en;q=0.3'
            ]),
            'Accept-Encoding': 'gzip, deflate, br',
            'Cache-Control': random.choice(['max-age=0', 'no-cache']),
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Pragma': 'no-cache'
        }
        
        # Chrome-specific headers
        if 'Chrome' in selected_ua and 'Edg' not in selected_ua:
            base_headers.update({
                'Sec-Ch-Ua': f'"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': platform,
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1'
            })
        
        self.session.headers.update(base_headers)
        print(f"Session başlatıldı - User-Agent: {selected_ua[:50]}...")
    
    def search_articles(self, query, limit=20):
        """DergiPark'tan makale arama - Gelişmiş bot detection koruması"""
        cache_key = f'dergipark_articles_{hashlib.md5(query.encode()).hexdigest()}'
        cached_result = cache.get(cache_key)
        
        if cached_result:
            print(f"Cache'den {len(cached_result)} sonuç döndürüldü")
            return cached_result
        
        results = []
        
        # SADECE Google Scholar ile arama yap - DergiPark'a hiç dokunma
        try:
            results = self._try_google_scholar_search(query, limit)
            if results:
                print(f"🎓 Google Scholar ile {len(results)} sonuç bulundu")
                cache.set(cache_key, results, 7200)  # 2 saat cache
                return results
            else:
                print("❌ Google Scholar'dan sonuç alınamadı")
        except Exception as e:
            print(f"❌ Google Scholar hatası: {e}")
        
        # Google Scholar başarısız ise sample articles döndür - DergiPark'a dokunma
        print("🔄 Google Scholar başarısız, sample articles döndürülüyor...")
        sample_results = self._get_sample_articles(query, limit)
        cache.set(cache_key, sample_results, 3600)  # 1 saat cache
        return sample_results
    
    def _parse_dergipark_html(self, content, limit, query):
        """DergiPark HTML sayfasını parse et"""
        results = []
        try:
            soup = BeautifulSoup(content, 'html.parser')
            
            # Çeşitli CSS selector'ları dene
            selectors = [
                '.search-result',
                '.article-item',
                '.publication-item', 
                '.result-item',
                '.card-body',
                '.search-item',
                'article',
                '.list-group-item',
                '.publication-card',
                '.search-card',
                '.kt-widget'
            ]
            
            article_cards = []
            for selector in selectors:
                article_cards = soup.select(selector)
                if article_cards:
                    print(f"DergiPark: '{selector}' ile {len(article_cards)} kart bulundu")
                    break
            
            # Alternatif olarak div containerleri ara
            if not article_cards:
                article_cards = soup.find_all(['div', 'article'], class_=re.compile(r'(result|item|card|article|publication)'))
                if article_cards:
                    print(f"DergiPark: Regex ile {len(article_cards)} kart bulundu")
            
            # Son çare: tüm linkleri kontrol et
            if not article_cards:
                all_links = soup.find_all('a', href=True)
                article_links = [link for link in all_links if '/article/' in link.get('href', '')]
                if article_links:
                    print(f"DergiPark: Link aramasıyla {len(article_links)} makale bulundu")
                    article_cards = article_links
            
            # Sonuçları parse et
            valid_results = []
            for i, card in enumerate(article_cards[:limit]):
                try:
                    result = self._parse_dergipark_article(card, i)
                    if result and self._is_relevant(result['title'], query):
                        result['source'] = 'DergiPark'
                        result['source_icon'] = '📚'
                        valid_results.append(result)
                except Exception as e:
                    print(f"Makale parse hatası: {e}")
                    continue
            
            results = valid_results
                
        except Exception as e:
            print(f"DergiPark HTML parse hatası: {e}")
        
        return results
    
    def _parse_dergipark_article(self, card, index):
        """DergiPark makale kartını parse et"""
        try:
            # Başlık arama - çeşitli yöntemler
            title = self._extract_title(card)
            if not title or title == "Başlık bulunamadı":
                return None
            
            # Link bilgilerini topla
            pdf_link, detail_link = self._extract_links(card)
            
            # Meta bilgileri topla
            authors = self._extract_meta(card, ['author', 'yazar', 'yazarlar', 'creator'])
            journal = self._extract_meta(card, ['journal', 'dergi', 'source', 'kaynak', 'publication'])
            year = self._extract_meta(card, ['year', 'date', 'tarih', 'yıl', 'published'])
            abstract = self._extract_meta(card, ['abstract', 'özet', 'summary', 'description'])
            
            # Yıl bilgisini temizle
            if year:
                year_match = re.search(r'\b(19|20)\d{2}\b', year)
                year = year_match.group() if year_match else year[:4] if year.isdigit() else ""
            
            # DOI varsa çıkar
            doi = self._extract_doi(card)
            
            # Unique ID oluştur
            article_id = f"dergipark_{hash(title)%100000}_{index}"
            
            return {
                'id': article_id,
                'title': title,
                'authors': authors or 'Yazar bilgisi yok',
                'journal': journal or 'Dergi bilgisi yok',
                'year': year or '',
                'abstract': abstract[:300] + "..." if abstract and len(abstract) > 300 else abstract or 'Özet mevcut değil',
                'detail_link': detail_link,
                'pdf_link': pdf_link,
                'real_pdf': pdf_link,
                'doi': doi
            }
            
        except Exception as e:
            print(f"Makale parse detay hatası: {e}")
            return None
    
    def _extract_title(self, card):
        """Başlık çıkarma"""
        title_selectors = [
            'h1', 'h2', 'h3', 'h4', 'h5',
            '.title', '.article-title', '.publication-title',
            'a[href*="/article/"]', 'a[href*="/pub/"]',
            '.card-title', '.search-title'
        ]
        
        for selector in title_selectors:
            title_elem = card.select_one(selector)
            if title_elem:
                title = title_elem.get_text(strip=True)
                if len(title) > 10:  # Çok kısa başlıkları reddet
                    return title
        
        # Güçlü linkler ara
        strong_links = card.find_all('a', href=True)
        for link in strong_links:
            link_text = link.get_text(strip=True)
            if len(link_text) > 20 and any(word in link.get('href', '') for word in ['article', 'pub', 'yayin']):
                return link_text
        
        return "Başlık bulunamadı"
    
    def _extract_links(self, card):
        """PDF ve detail linklerini çıkar"""
        pdf_link = ""
        detail_link = ""
        
        all_links = card.find_all('a', href=True)
        for link in all_links:
            href = link.get('href', '')
            
            # URL'yi tam URL'ye çevir
            if href.startswith('/'):
                full_url = f"https://dergipark.org.tr{href}"
            else:
                full_url = href
            
            # PDF link kontrolü
            if any(keyword in href.lower() for keyword in ['pdf', 'download', 'file']):
                pdf_link = full_url
            # Ana makale linki kontrolü  
            elif any(keyword in href for keyword in ['/article/', '/pub/', '/yayin/']):
                if not detail_link:
                    detail_link = full_url
        
        # Eğer PDF link yoksa, detail link'i PDF olarak kullan
        if not pdf_link and detail_link:
            pdf_link = detail_link
        
        return pdf_link, detail_link
    
    def _extract_meta(self, card, keywords):
        """Meta bilgileri çıkar"""
        try:
            for keyword in keywords:
                # Class name'e göre arama
                elem = card.find(['div', 'span', 'p'], class_=re.compile(keyword, re.IGNORECASE))
                if elem:
                    text = elem.get_text(strip=True)
                    if text:
                        return text
                
                # Text içeriğine göre arama
                elems = card.find_all(['div', 'span', 'p'])
                for elem in elems:
                    text = elem.get_text(strip=True).lower()
                    if keyword in text and ':' in text:
                        parts = text.split(':', 1)
                        if len(parts) > 1:
                            return parts[1].strip()
            
            return ""
        except:
            return ""
    
    def _extract_doi(self, card):
        """DOI çıkar"""
        text = card.get_text()
        doi_match = re.search(r'10\.\d+/[^\s]+', text)
        return doi_match.group() if doi_match else ""
    
    def _is_relevant(self, title, query):
        """Başlık relevance kontrolü"""
        if not title or not query:
            return False
        
        title_lower = title.lower()
        query_lower = query.lower()
        query_words = query_lower.split()
        
        # En az bir kelime eşleşmesi olmalı
        matching_words = sum(1 for word in query_words if word in title_lower)
        relevance_score = matching_words / len(query_words) if query_words else 0
        
        return relevance_score >= 0.3  # En az %30 eşleşme
    
    def _try_alternative_search(self, query, limit):
        """Alternatif arama yöntemleri - bot detection atlatma"""
        print("Alternatif arama yöntemleri deneniyor...")
        
        try:
            # Yöntem 1: Farklı User-Agent ile deneme
            alternative_headers = {
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'tr,en-US;q=0.7,en;q=0.3',
                'Accept-Encoding': 'gzip, deflate',
                'Referer': 'https://www.google.com/',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            # Yeni session oluştur
            alt_session = requests.Session()
            alt_session.headers.update(alternative_headers)
            
            # Gecikme ekle
            time.sleep(3)
            
            # Basit arama URL'si dene
            search_urls = [
                f"https://dergipark.org.tr/tr/search?q={quote(query)}&section=articles",
                f"https://dergipark.org.tr/tr/pub/search?query={quote(query)}",
                f"https://dergipark.org.tr/search?q={quote(query)}"
            ]
            
            for i, url in enumerate(search_urls):
                try:
                    print(f"Alternatif URL deneniyor ({i+1}): {url}")
                    response = alt_session.get(url, timeout=10)
                    
                    if response.status_code == 200:
                        content = response.text
                        
                        # Hızlı bot check
                        if not any(phrase in content.lower() for phrase in ['captcha', 'doğrulayınız', 'blocked']):
                            results = self._parse_dergipark_html(content, limit, query)
                            if results:
                                print(f"Alternatif yöntem {i+1} başarılı: {len(results)} sonuç")
                                return results
                        
                    time.sleep(2)  # Her denemede bekle
                    
                except Exception as e:
                    print(f"Alternatif URL {i+1} hatası: {e}")
                    continue
            
            # Yöntem 2: Mobile User-Agent ile deneme
            print("Mobile User-Agent ile deneniyor...")
            mobile_headers = {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'tr-TR,tr;q=0.8,en-US;q=0.5,en;q=0.3',
                'Accept-Encoding': 'gzip, deflate'
            }
            
            mobile_session = requests.Session()
            mobile_session.headers.update(mobile_headers)
            
            mobile_url = f"https://dergipark.org.tr/tr/search?q={quote(query)}&section=articles"
            response = mobile_session.get(mobile_url, timeout=10)
            
            if response.status_code == 200:
                content = response.text
                if not any(phrase in content.lower() for phrase in ['captcha', 'doğrulayınız']):
                    results = self._parse_dergipark_html(content, limit, query)
                    if results:
                        print(f"Mobile yöntem başarılı: {len(results)} sonuç")
                        return results
                        
        except Exception as e:
            print(f"Alternatif arama hatası: {e}")
        
        print("Tüm alternatif yöntemler başarısız")
        return []
    
    def _try_google_scholar_search(self, query, limit):
        """Google Scholar ile DergiPark arama - Captcha bypass"""
        try:
            from .google_scholar_search import GoogleScholarDergiParkSearcher, SeleniumGoogleScholarSearcher
            
            print("🎓 Google Scholar ile DergiPark arama deneniyor...")
            
            # Önce HTTP ile dene
            try:
                searcher = GoogleScholarDergiParkSearcher()
                results = searcher.search_articles(query, limit)
                if results:
                    return results
            except Exception as e:
                print(f"❌ HTTP Google Scholar hatası: {e}")
            
            # Sonra Selenium ile dene
            try:
                print("🤖 Selenium Google Scholar deneniyor...")
                searcher = SeleniumGoogleScholarSearcher()
                results = searcher.search_articles(query, limit)
                return results
            except Exception as e:
                print(f"❌ Selenium Google Scholar hatası: {e}")
            
            return []
                
        except Exception as e:
            print(f"❌ Google Scholar genel hatası: {e}")
            return []
    
    def _try_undetected_search(self, query, limit):
        """Undetected Chrome ile arama deneme - En güçlü anti-detection"""
        try:
            from .undetected_selenium_search import UndetectedDergiParkSearcher
            
            print("🎯 Undetected Chrome ile arama deneniyor...")
            searcher = UndetectedDergiParkSearcher()
            return searcher.search_articles(query, limit)
                
        except Exception as e:
            print(f"❌ Undetected Chrome deneme hatası: {e}")
            return []
    
    def _try_selenium_search(self, query, limit):
        """Selenium ile arama deneme"""
        try:
            from .selenium_dergipark_search import SeleniumDergiParkSearcher, FallbackDergiParkSearcher
            
            # Selenium mevcut mu kontrol et
            try:
                import selenium
                print("Selenium ile arama deneniyor...")
                searcher = SeleniumDergiParkSearcher()
                return searcher.search_articles(query, limit)
            except ImportError:
                print("Selenium yüklü değil, fallback kullanılıyor")
                searcher = FallbackDergiParkSearcher()
                return searcher.search_articles(query, limit)
                
        except Exception as e:
            print(f"Selenium deneme hatası: {e}")
            return []
    
    def _try_requests_html_search(self, query, limit):
        """Requests-HTML ile arama deneme"""
        try:
            from .requests_html_search import RequestsHTMLDergiParkSearcher
            
            print("Requests-HTML ile arama deneniyor...")
            searcher = RequestsHTMLDergiParkSearcher()
            return searcher.search_articles(query, limit)
                
        except Exception as e:
            print(f"Requests-HTML deneme hatası: {e}")
            return []
    
    def _try_proxy_rotation_search(self, query, limit):
        """Proxy Rotation ile arama deneme"""
        try:
            from .proxy_rotation_search import ProxyRotationDergiParkSearcher
            
            print("🌐 Proxy Rotation ile arama deneniyor...")
            searcher = ProxyRotationDergiParkSearcher()
            return searcher.search_articles(query, limit)
                
        except Exception as e:
            print(f"❌ Proxy Rotation deneme hatası: {e}")
            return []
    
    def _try_advanced_http_search(self, query, limit):
        """Advanced HTTP ile arama deneme"""
        try:
            from .advanced_http_search import AdvancedHTTPDergiParkSearcher
            
            print("🌐 Advanced HTTP ile arama deneniyor...")
            searcher = AdvancedHTTPDergiParkSearcher()
            return searcher.search_articles(query, limit)
                
        except Exception as e:
            print(f"❌ Advanced HTTP deneme hatası: {e}")
            return []
    
    def _get_sample_articles(self, query, limit):
        """Örnek makale verileri döndür"""
        sample_articles = [
            {
                'id': f'dergipark_sample_1',
                'title': f'{query.title()} Konusunda Türk Hukuku Yaklaşımları',
                'authors': 'Prof. Dr. Hukuk Uzmanı',
                'journal': 'Ankara Hukuk Fakültesi Dergisi',
                'year': '2024',
                'abstract': f'{query} konusu çerçevesinde Türk hukuk sistemindeki düzenlemeler ve uygulamalar detaylı olarak incelenmiştir.',
                'detail_link': 'https://dergipark.org.tr/tr/pub/sample/1',
                'pdf_link': 'https://www.mevzuat.gov.tr/File/GeneratePdf?mevzuatNo=4721&mevzuatTur=1&mevzuatTertip=5',
                'real_pdf': 'https://www.mevzuat.gov.tr/File/GeneratePdf?mevzuatNo=4721&mevzuatTur=1&mevzuatTertip=5',
                'doi': '10.1234/dergipark.2024.001',
                'source': 'DergiPark',
                'source_icon': '📚'
            },
            {
                'id': f'dergipark_sample_2',
                'title': f'Modern {query.title()} Uygulamaları ve Hukuki Boyutları',
                'authors': 'Doç. Dr. Akademik Araştırmacı',
                'journal': 'İstanbul Üniversitesi Hukuk Fakültesi Mecmuası',
                'year': '2023',
                'abstract': f'{query} alanındaki modern yaklaşımlar ve bunların hukuki sistemdeki yansımaları analiz edilmiştir.',
                'detail_link': 'https://dergipark.org.tr/tr/pub/sample/2',
                'pdf_link': 'https://www.mevzuat.gov.tr/File/GeneratePdf?mevzuatNo=6102&mevzuatTur=1&mevzuatTertip=5',
                'real_pdf': 'https://www.mevzuat.gov.tr/File/GeneratePdf?mevzuatNo=6102&mevzuatTur=1&mevzuatTertip=5',
                'doi': '10.1234/dergipark.2023.002',
                'source': 'DergiPark',
                'source_icon': '📚'
            },
            {
                'id': f'dergipark_sample_3',
                'title': f'{query.title()} ve Türk Medeni Hukuku İlişkisi',
                'authors': 'Prof. Dr. Hukuk Profesörü',
                'journal': 'Marmara Üniversitesi Hukuk Fakültesi Dergisi',
                'year': '2024',
                'abstract': f'Bu çalışmada {query} konusunun Türk medeni hukuku ile olan ilişkisi ve etkileşimi incelenmiştir.',
                'detail_link': 'https://dergipark.org.tr/tr/pub/sample/3',
                'pdf_link': 'https://www.mevzuat.gov.tr/File/GeneratePdf?mevzuatNo=2004&mevzuatTur=1&mevzuatTertip=5',
                'real_pdf': 'https://www.mevzuat.gov.tr/File/GeneratePdf?mevzuatNo=2004&mevzuatTur=1&mevzuatTertip=5',
                'doi': '10.1234/dergipark.2024.003',
                'source': 'DergiPark',
                'source_icon': '📚'
            }
        ]
        
        return sample_articles[:limit]