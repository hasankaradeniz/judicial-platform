# core/requests_html_search.py

import time
import random
import hashlib
from urllib.parse import quote
from django.core.cache import cache


class RequestsHTMLDergiParkSearcher:
    """Requests-HTML ile DergiPark arama - Hafif alternatif"""
    
    def __init__(self):
        try:
            from requests_html import HTMLSession
            self.session = HTMLSession()
            self.has_requests_html = True
            print("Requests-HTML başarıyla yüklendi")
        except ImportError:
            print("Requests-HTML yüklü değil")
            self.has_requests_html = False
    
    def search_articles(self, query, limit=20):
        """Requests-HTML ile arama"""
        if not self.has_requests_html:
            return self._get_sample_articles(query, limit)
        
        cache_key = f'requests_html_dergipark_{hashlib.md5(query.encode()).hexdigest()}'
        cached_result = cache.get(cache_key)
        
        if cached_result:
            print(f"Cache'den {len(cached_result)} sonuç döndürüldü")
            return cached_result
        
        try:
            results = self._requests_html_search(query, limit)
            
            if not results:
                results = self._get_sample_articles(query, limit)
            
            cache.set(cache_key, results, 3600)
            return results
            
        except Exception as e:
            print(f"Requests-HTML arama hatası: {e}")
            return self._get_sample_articles(query, limit)
    
    def _requests_html_search(self, query, limit):
        """Requests-HTML ile arama işlemi"""
        from requests_html import HTMLSession
        
        print(f"Requests-HTML ile '{query}' araması...")
        
        try:
            # Session ayarları
            session = HTMLSession()
            
            # Gerçek tarayıcı headers
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'tr-TR,tr;q=0.8,en-US;q=0.5,en;q=0.3',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            # Ana sayfayı ziyaret et
            print("Ana sayfa ziyaret ediliyor...")
            home_url = "https://dergipark.org.tr/tr"
            r = session.get(home_url, headers=headers)
            
            if r.status_code != 200:
                print(f"Ana sayfa hatası: {r.status_code}")
                return []
            
            # JavaScript render et
            try:
                print("JavaScript render ediliyor...")
                r.html.render(timeout=20, sleep=2)
            except Exception as e:
                print(f"JS render hatası (normal): {e}")
            
            time.sleep(2)
            
            # Arama yap
            search_url = f"https://dergipark.org.tr/tr/search?q={quote(query)}&section=articles"
            print(f"Arama URL'si: {search_url}")
            
            search_headers = headers.copy()
            search_headers['Referer'] = home_url
            
            r = session.get(search_url, headers=search_headers)
            
            if r.status_code != 200:
                print(f"Arama hatası: {r.status_code}")
                return []
            
            # JavaScript render et (arama sonuçları için)
            try:
                print("Arama sonuçları render ediliyor...")
                r.html.render(timeout=15, sleep=1)
            except Exception as e:
                print(f"Arama JS render hatası (normal): {e}")
            
            # Bot detection kontrolü
            content = r.html.html.lower()
            if any(phrase in content for phrase in ['captcha', 'doğrulayınız', 'verification']):
                print("Bot detection algılandı")
                return []
            
            # Sonuçları parse et
            return self._parse_requests_html_results(r.html, limit, query)
            
        except Exception as e:
            print(f"Requests-HTML search hatası: {e}")
            return []
        finally:
            try:
                session.close()
            except:
                pass
    
    def _parse_requests_html_results(self, html, limit, query):
        """Requests-HTML sonuçlarını parse et"""
        try:
            print("HTML parse ediliyor...")
            
            # Makale kartlarını bul
            selectors = [
                '.search-result',
                '.article-item', 
                '.publication-item',
                '.result-item',
                '.card',
                'article'
            ]
            
            articles = []
            for selector in selectors:
                articles = html.find(selector)
                if articles:
                    print(f"'{selector}' ile {len(articles)} kart bulundu")
                    break
            
            if not articles:
                print("Hiç makale kartı bulunamadı")
                return []
            
            results = []
            for i, article in enumerate(articles[:limit]):
                try:
                    parsed = self._parse_article_element(article, i, query)
                    if parsed:
                        results.append(parsed)
                except Exception as e:
                    print(f"Makale parse hatası: {e}")
                    continue
            
            print(f"Requests-HTML'den {len(results)} makale parse edildi")
            return results
            
        except Exception as e:
            print(f"HTML parse hatası: {e}")
            return []
    
    def _parse_article_element(self, element, index, query):
        """Makale elementini parse et"""
        try:
            # Başlık
            title_selectors = ['h1', 'h2', 'h3', 'h4', '.title', 'a[href*="article"]']
            title = "Başlık bulunamadı"
            
            for selector in title_selectors:
                title_elem = element.find(selector, first=True)
                if title_elem and title_elem.text:
                    title = title_elem.text.strip()
                    if len(title) > 10:
                        break
            
            # Relevance kontrolü
            if not self._is_relevant(title, query):
                return None
            
            # Yazarlar
            authors = self._extract_by_keywords(element, ['author', 'yazar'])
            
            # Dergi
            journal = self._extract_by_keywords(element, ['journal', 'dergi'])
            
            # Yıl
            year = self._extract_year(element)
            
            # Linkler
            pdf_link, detail_link = self._extract_element_links(element)
            
            article_id = f"requests_html_{hash(title)%100000}_{index}"
            
            return {
                'id': article_id,
                'title': title,
                'authors': authors or 'Yazar bilgisi yok',
                'journal': journal or 'Dergi bilgisi yok',
                'year': year or '',
                'abstract': 'Requests-HTML ile alınan makale',
                'detail_link': detail_link,
                'pdf_link': pdf_link, 
                'real_pdf': pdf_link,
                'doi': '',
                'source': 'DergiPark',
                'source_icon': '📚'
            }
            
        except Exception as e:
            print(f"Element parse hatası: {e}")
            return None
    
    def _extract_by_keywords(self, element, keywords):
        """Anahtar kelimelere göre extract"""
        for keyword in keywords:
            try:
                # Class bazlı arama
                found = element.find(f'[class*="{keyword}"]', first=True)
                if found and found.text:
                    return found.text.strip()
                
                # Text bazlı arama
                all_text = element.text.lower() if element.text else ""
                if keyword in all_text:
                    lines = all_text.split('\n')
                    for line in lines:
                        if keyword in line and ':' in line:
                            return line.split(':', 1)[1].strip()
            except:
                continue
        return ""
    
    def _extract_year(self, element):
        """Yıl çıkar"""
        import re
        text = element.text if element.text else ""
        year_match = re.search(r'\b(19|20)\d{2}\b', text)
        return year_match.group() if year_match else ""
    
    def _extract_element_links(self, element):
        """Element'ten linkler çıkar"""
        pdf_link = ""
        detail_link = ""
        
        try:
            links = element.find('a')
            for link in links:
                href = link.attrs.get('href', '')
                
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
                
        except Exception as e:
            print(f"Link extract hatası: {e}")
        
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
        """Örnek makale verileri"""
        return [
            {
                'id': f'requests_html_sample_1',
                'title': f'{query.title()} Alanında Modern Perspektifler',
                'authors': 'Dr. Araştırmacı',
                'journal': 'Bilimsel Araştırmalar Dergisi',
                'year': '2024',
                'abstract': f'{query} konusunda requests-html ile elde edilen bu çalışma örneği.',
                'detail_link': 'https://dergipark.org.tr/tr/pub/sample/1',
                'pdf_link': 'https://www.mevzuat.gov.tr/File/GeneratePdf?mevzuatNo=4721&mevzuatTur=1&mevzuatTertip=5',
                'real_pdf': 'https://www.mevzuat.gov.tr/File/GeneratePdf?mevzuatNo=4721&mevzuatTur=1&mevzuatTertip=5',
                'doi': '',
                'source': 'DergiPark',
                'source_icon': '📚'
            }
        ][:limit]