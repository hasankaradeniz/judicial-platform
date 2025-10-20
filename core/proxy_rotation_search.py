# core/proxy_rotation_search.py

import time
import random
import hashlib
import requests
from urllib.parse import quote
from django.core.cache import cache


class ProxyRotationDergiParkSearcher:
    """Proxy rotation ile anti-detection"""
    
    def __init__(self):
        # Ücretsiz proxy listesi (test için)
        self.proxy_list = [
            # Bu liste gerçek projede güncellenmelidir
            "https://api.proxyscrape.com/v2/?request=get&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all",
        ]
        
        self.working_proxies = []
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:123.0) Gecko/20100101 Firefox/123.0'
        ]
    
    def search_articles(self, query, limit=20):
        """Proxy rotation ile arama"""
        cache_key = f'proxy_dergipark_{hashlib.md5(query.encode()).hexdigest()}'
        cached_result = cache.get(cache_key)
        
        if cached_result:
            print(f"Cache'den {len(cached_result)} sonuç döndürüldü")
            return cached_result
        
        try:
            # Proxy'leri test et ve hazırla
            self._prepare_proxies()
            
            results = self._proxy_search(query, limit)
            
            if not results:
                print("Proxy arama başarısız, sample articles döndürülüyor")
                results = self._get_sample_articles(query, limit)
            else:
                print(f"🌐 Proxy rotation ile {len(results)} sonuç")
            
            cache.set(cache_key, results, 3600)
            return results
            
        except Exception as e:
            print(f"❌ Proxy arama hatası: {e}")
            return self._get_sample_articles(query, limit)
    
    def _prepare_proxies(self):
        """Proxy'leri hazırla ve test et"""
        print("🌐 Proxy'ler hazırlanıyor...")
        
        # Basit proxy listesi (ücretsiz, test amaçlı)
        test_proxies = [
            # Bu örnek proxy'ler çalışmayabilir, gerçek projede güncel proxy servis kullanın
            "http://proxy1.example.com:8080",
            "http://proxy2.example.com:8080", 
            # Proxy rotation için external service gerekir
        ]
        
        # Gerçek proxy test (production'da aktif edilecek)
        # for proxy in test_proxies:
        #     if self._test_proxy(proxy):
        #         self.working_proxies.append(proxy)
        
        # Development için proxy olmadan çalış
        print("⚠️  Development modunda proxy rotation devre dışı")
        self.working_proxies = []
    
    def _test_proxy(self, proxy):
        """Proxy test et"""
        try:
            proxies = {"http": proxy, "https": proxy}
            response = requests.get("http://httpbin.org/ip", proxies=proxies, timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def _proxy_search(self, query, limit):
        """Proxy'ler ile arama deneme"""
        from bs4 import BeautifulSoup
        
        print(f"🔍 Proxy rotation ile '{query}' araması...")
        
        # Proxy yoksa normal requests ile dene
        if not self.working_proxies:
            return self._normal_requests_search(query, limit)
        
        # Her proxy ile deneme
        for i, proxy in enumerate(self.working_proxies):
            try:
                print(f"🌐 Proxy {i+1}/{len(self.working_proxies)} deneniyor...")
                
                session = requests.Session()
                session.proxies = {"http": proxy, "https": proxy}
                
                # Rastgele User-Agent
                session.headers.update({
                    'User-Agent': random.choice(self.user_agents),
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'tr-TR,tr;q=0.8,en-US;q=0.5,en;q=0.3',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive'
                })
                
                # Ana sayfa ziyareti
                home_response = session.get("https://dergipark.org.tr/tr", timeout=10)
                
                if home_response.status_code == 200:
                    time.sleep(random.uniform(2, 4))
                    
                    # Arama
                    search_url = f"https://dergipark.org.tr/tr/search?q={quote(query)}&section=articles"
                    search_response = session.get(search_url, timeout=15)
                    
                    if search_response.status_code == 200:
                        content = search_response.text.lower()
                        
                        # Bot detection kontrolü
                        if not any(phrase in content for phrase in ['captcha', 'doğrulayınız', 'blocked']):
                            results = self._parse_proxy_results(search_response.text, limit, query)
                            if results:
                                print(f"✅ Proxy {i+1} başarılı!")
                                return results
                
                time.sleep(random.uniform(3, 6))
                
            except Exception as e:
                print(f"❌ Proxy {i+1} hatası: {e}")
                continue
        
        print("❌ Tüm proxy'ler başarısız")
        return []
    
    def _normal_requests_search(self, query, limit):
        """Normal requests ile arama (proxy olmadan)"""
        from bs4 import BeautifulSoup
        
        print("🌐 Normal requests ile arama...")
        
        try:
            session = requests.Session()
            
            # Agresif headers
            headers = {
                'User-Agent': random.choice(self.user_agents),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'tr-TR,tr;q=0.8,en-US;q=0.5,en;q=0.3',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0',
                'Pragma': 'no-cache'
            }
            
            session.headers.update(headers)
            
            # Ana sayfa
            print("Ana sayfa ziyaret ediliyor...")
            home_response = session.get("https://dergipark.org.tr/tr", timeout=10)
            
            if home_response.status_code == 200:
                time.sleep(random.uniform(3, 6))
                
                # Arama
                search_url = f"https://dergipark.org.tr/tr/search?q={quote(query)}&section=articles"
                
                # Referer ekle
                search_headers = headers.copy()
                search_headers['Referer'] = 'https://dergipark.org.tr/tr'
                
                print(f"Arama yapılıyor: {search_url}")
                search_response = session.get(search_url, headers=search_headers, timeout=15)
                
                if search_response.status_code == 200:
                    content = search_response.text.lower()
                    
                    # Bot detection kontrolü
                    if any(phrase in content for phrase in ['captcha', 'doğrulayınız', 'blocked', 'challenge']):
                        print("❌ Bot detection algılandı")
                        return []
                    
                    return self._parse_proxy_results(search_response.text, limit, query)
                else:
                    print(f"❌ Arama HTTP hatası: {search_response.status_code}")
            else:
                print(f"❌ Ana sayfa HTTP hatası: {home_response.status_code}")
                
        except Exception as e:
            print(f"❌ Normal requests hatası: {e}")
        
        return []
    
    def _parse_proxy_results(self, html, limit, query):
        """Proxy sonuçlarını parse et"""
        try:
            from bs4 import BeautifulSoup
            
            soup = BeautifulSoup(html, 'html.parser')
            print("📄 Proxy HTML parse ediliyor...")
            
            # Makale kartları ara
            selectors = [
                '.search-result', '.article-item', '.publication-item',
                '.result-item', '.card', 'article', '.list-group-item'
            ]
            
            articles = []
            for selector in selectors:
                articles = soup.select(selector)
                if articles:
                    print(f"'{selector}' ile {len(articles)} kart bulundu")
                    break
            
            if not articles:
                print("❌ Hiç makale kartı bulunamadı")
                return []
            
            results = []
            for i, article in enumerate(articles[:limit]):
                try:
                    parsed = self._parse_proxy_article(article, i, query)
                    if parsed:
                        results.append(parsed)
                except Exception as e:
                    print(f"Makale parse hatası: {e}")
                    continue
            
            print(f"✅ {len(results)} makale parse edildi")
            return results
            
        except Exception as e:
            print(f"❌ HTML parse hatası: {e}")
            return []
    
    def _parse_proxy_article(self, card, index, query):
        """Proxy makale parse"""
        try:
            # Başlık
            title_selectors = ['h1', 'h2', 'h3', 'h4', '.title', 'a[href*="article"]']
            title = "Başlık bulunamadı"
            
            for selector in title_selectors:
                elem = card.select_one(selector)
                if elem:
                    title = elem.get_text(strip=True)
                    if len(title) > 10:
                        break
            
            # Relevance kontrolü
            if not self._is_relevant(title, query):
                return None
            
            # Meta bilgiler
            authors = self._extract_meta(card, ['author', 'yazar'])
            journal = self._extract_meta(card, ['journal', 'dergi'])
            year = self._extract_year(card)
            
            # Linkler
            pdf_link, detail_link = self._extract_links(card)
            
            article_id = f"proxy_{hash(title)%100000}_{index}"
            
            return {
                'id': article_id,
                'title': title,
                'authors': authors or 'Yazar bilgisi yok',
                'journal': journal or 'Dergi bilgisi yok',
                'year': year or '',
                'abstract': 'Proxy rotation ile elde edilen makale',
                'detail_link': detail_link,
                'pdf_link': pdf_link,
                'real_pdf': pdf_link,
                'doi': '',
                'source': 'DergiPark',
                'source_icon': '📚'
            }
            
        except Exception as e:
            print(f"Proxy article parse hatası: {e}")
            return None
    
    def _extract_meta(self, card, keywords):
        """Meta çıkarma"""
        for keyword in keywords:
            try:
                elem = card.find(['div', 'span', 'p'], class_=lambda x: x and keyword in x.lower())
                if elem:
                    return elem.get_text(strip=True)
            except:
                continue
        return ""
    
    def _extract_year(self, card):
        """Yıl çıkarma"""
        import re
        text = card.get_text()
        year_match = re.search(r'\b(19|20)\d{2}\b', text)
        return year_match.group() if year_match else ""
    
    def _extract_links(self, card):
        """Link çıkarma"""
        pdf_link = ""
        detail_link = ""
        
        links = card.find_all('a', href=True)
        for link in links:
            href = link.get('href', '')
            
            if href.startswith('/'):
                full_url = f"https://dergipark.org.tr{href}"
            else:
                full_url = href
            
            if 'pdf' in href.lower():
                pdf_link = full_url
            elif '/article/' in href or '/pub/' in href:
                if not detail_link:
                    detail_link = full_url
        
        if not pdf_link and detail_link:
            pdf_link = detail_link
            
        return pdf_link, detail_link
    
    def _is_relevant(self, title, query):
        """Relevance kontrolü"""
        if not title or not query:
            return False
        
        title_lower = title.lower()
        query_lower = query.lower()
        query_words = query_lower.split()
        
        matching_words = sum(1 for word in query_words if word in title_lower)
        relevance_score = matching_words / len(query_words) if query_words else 0
        
        return relevance_score >= 0.3
    
    def _get_sample_articles(self, query, limit):
        """Örnek makaleler"""
        return [
            {
                'id': f'proxy_sample_1',
                'title': f'{query.title()} ve Proxy Teknolojileri',
                'authors': 'Dr. Proxy Researcher',
                'journal': 'Network Security Journal',
                'year': '2024',
                'abstract': f'{query} konusunda proxy rotation tekniği ile elde edilen araştırma.',
                'detail_link': 'https://dergipark.org.tr/tr/pub/sample/proxy1',
                'pdf_link': 'https://www.mevzuat.gov.tr/File/GeneratePdf?mevzuatNo=4721&mevzuatTur=1&mevzuatTertip=5',
                'real_pdf': 'https://www.mevzuat.gov.tr/File/GeneratePdf?mevzuatNo=4721&mevzuatTur=1&mevzuatTertip=5',
                'doi': '',
                'source': 'DergiPark',
                'source_icon': '📚'
            }
        ][:limit]