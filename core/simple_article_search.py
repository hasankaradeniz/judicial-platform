# core/simple_article_search.py

import requests
import time
import random
import hashlib
from django.core.cache import cache
from datetime import datetime


class SimpleArticleSearcher:
    """Basit ve güvenilir makale arama sistemi - Sadece API'ler"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Academic Research Tool (contact@research.com)',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
    
    def search_articles(self, query, limit=20, page=1):
        """Ana arama fonksiyonu - paginated"""
        offset = (page - 1) * 10  # 10'arlı sayfalar
        
        # Cache kontrolü (page'e göre)
        cached_result = None
        try:
            cache_key = f'simple_articles_{hashlib.md5(query.encode()).hexdigest()}_page_{page}'
            cached_result = cache.get(cache_key)
            if cached_result:
                print(f"📚 Cache'den sayfa {page} için {len(cached_result)} makale döndürüldü")
                return cached_result
        except Exception as e:
            print(f"Cache hatası (devam ediliyor): {e}")
            cached_result = None
        
        print(f"🔍 '{query}' sayfa {page} için makale aranıyor...")
        results = []
        
        # Her sayfa için daha fazla sonuç çek
        crossref_rows = 50 + offset  # Daha fazla sonuç al
        doaj_rows = 30 + offset
        
        # 1. CrossRef API (En güvenilir)
        print(f"🔍 CrossRef API'sine bağlanıyor (sayfa {page})...")
        crossref_results = self._search_crossref(query, crossref_rows, offset)
        if crossref_results:
            results.extend(crossref_results)
            print(f"✅ CrossRef: {len(crossref_results)} makale")
        else:
            print(f"❌ CrossRef: 0 makale")
        
        # 2. DOAJ API (Açık erişim)
        print(f"🔍 DOAJ API'sine bağlanıyor (sayfa {page})...")
        doaj_results = self._search_doaj(query, doaj_rows, offset)
        if doaj_results:
            results.extend(doaj_results)
            print(f"✅ DOAJ: {len(doaj_results)} makale")
        else:
            print(f"❌ DOAJ: 0 makale")
        
        # 3. Sonuçları temizle ve sırala
        unique_results = self._clean_results(results, query)
        
        # Pagination: Sadece 10 makale döndür
        start_idx = offset % len(unique_results) if unique_results else 0
        end_idx = start_idx + 10
        final_results = unique_results[start_idx:end_idx] if unique_results else []
        
        # Cache'e kaydet (2 saat) - güvenli şekilde
        try:
            cache.set(cache_key, final_results, 7200)
        except Exception as e:
            print(f"Cache kaydetme hatası (devam ediliyor): {e}")
        
        print(f"📖 Toplam {len(final_results)} makale bulundu")
        return final_results
    
    def _search_crossref(self, query, rows, offset=0):
        """CrossRef API ile arama - paginated"""
        results = []
        try:
            url = "https://api.crossref.org/works"
            params = {
                'query': query,
                'rows': rows,
                'offset': offset,
                'sort': 'relevance',
                'filter': 'type:journal-article'
            }
            
            print(f"📡 CrossRef URL: {url}")
            print(f"📡 CrossRef params: {params}")
            
            response = self.session.get(url, params=params, timeout=15)
            print(f"📡 CrossRef response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                items = data.get('message', {}).get('items', [])
                print(f"📡 CrossRef raw items: {len(items)}")
                
                for i, item in enumerate(items):
                    article = self._parse_crossref_item(item)
                    if article:
                        results.append(article)
                        print(f"  ✅ Parse edildi: {article['title'][:50]}...")
                    else:
                        print(f"  ❌ Parse edilemedi: {i+1}")
            else:
                print(f"❌ CrossRef HTTP error: {response.status_code}")
                        
            time.sleep(0.5)  # Rate limiting
            
        except Exception as e:
            print(f"❌ CrossRef API hatası: {e}")
        
        print(f"📊 CrossRef final results: {len(results)}")
        return results
    
    def _search_doaj(self, query, page_size, offset=0):
        """DOAJ API ile arama - paginated"""
        results = []
        try:
            url = "https://doaj.org/api/search/articles"
            page_num = (offset // 10) + 1  # DOAJ page numbering
            params = {
                'query': query,
                'pageSize': min(page_size, 50),  # DOAJ limit
                'page': page_num,
                'sort': 'score:desc'
            }
            
            response = self.session.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                items = data.get('results', [])
                
                for item in items:
                    article = self._parse_doaj_item(item)
                    if article:
                        results.append(article)
                        
            time.sleep(0.5)  # Rate limiting
            
        except Exception as e:
            print(f"DOAJ API hatası: {e}")
        
        return results
    
    def _parse_crossref_item(self, item):
        """CrossRef makalesini parse et"""
        try:
            title = item.get('title', [''])[0] if item.get('title') else ''
            if not title or len(title) < 10:
                return None
            
            # Yazarlar
            authors = []
            if item.get('author'):
                for author in item['author'][:3]:  # İlk 3 yazar
                    given = author.get('given', '')
                    family = author.get('family', '')
                    if given and family:
                        authors.append(f"{given} {family}")
            authors_str = ', '.join(authors) if authors else 'Yazar bilgisi yok'
            
            # Dergi
            journal = ''
            if item.get('container-title'):
                journal = item['container-title'][0]
            
            # Yıl
            year = ''
            if item.get('published-print', {}).get('date-parts'):
                year = str(item['published-print']['date-parts'][0][0])
            elif item.get('published-online', {}).get('date-parts'):
                year = str(item['published-online']['date-parts'][0][0])
            
            # DOI ve linkler
            doi = item.get('DOI', '')
            detail_link = f"https://doi.org/{doi}" if doi else ''
            
            # Özet (varsa) - CrossRef'den gelmeyebilir, sonradan çekilecek
            abstract = item.get('abstract', '')
            if abstract and len(abstract) > 300:
                abstract = abstract[:300] + "..."
            elif not abstract:
                # Özet sonradan çekilecek
                abstract = 'Özet yükleniyor...'
            
            return {
                'id': f"crossref_{doi.replace('/', '_')}" if doi else f"crossref_{hash(title)%100000}",
                'title': title,
                'authors': authors_str,
                'journal': journal or 'Academic Journal',
                'year': year or '2024',
                'abstract': abstract,
                'detail_link': detail_link,
                'pdf_link': detail_link,
                'real_pdf': detail_link,
                'doi': doi,
                'source': 'CrossRef',
                'source_icon': '🔬'
            }
            
        except Exception:
            return None
    
    def _parse_doaj_item(self, item):
        """DOAJ makalesini parse et"""
        try:
            bibjson = item.get('bibjson', {})
            title = bibjson.get('title', '')
            
            if not title or len(title) < 10:
                return None
            
            # Yazarlar
            authors = []
            if bibjson.get('author'):
                for author in bibjson['author'][:3]:  # İlk 3 yazar
                    name = author.get('name', '')
                    if name:
                        authors.append(name)
            authors_str = ', '.join(authors) if authors else 'Yazar bilgisi yok'
            
            # Dergi
            journal = bibjson.get('journal', {}).get('title', 'Open Access Journal')
            
            # Yıl
            year = str(bibjson.get('year', '2024'))
            
            # DOI ve linkler
            doi = ''
            detail_link = ''
            pdf_link = ''
            
            if bibjson.get('identifier'):
                for identifier in bibjson['identifier']:
                    if identifier.get('type') == 'doi':
                        doi = identifier.get('id', '')
                        detail_link = f"https://doi.org/{doi}"
                        break
            
            if bibjson.get('link'):
                for link in bibjson['link']:
                    url = link.get('url', '')
                    link_type = link.get('type', '').lower()
                    
                    if 'pdf' in link_type or 'fulltext' in link_type:
                        pdf_link = url
                        if not detail_link:
                            detail_link = url
                        break
            
            # Özet
            abstract = bibjson.get('abstract', 'Bu açık erişim makalesi için özet mevcut değil')
            if len(abstract) > 300:
                abstract = abstract[:300] + "..."
            
            return {
                'id': f"doaj_{doi.replace('/', '_')}" if doi else f"doaj_{hash(title)%100000}",
                'title': title,
                'authors': authors_str,
                'journal': journal,
                'year': year,
                'abstract': abstract,
                'detail_link': detail_link or pdf_link,
                'pdf_link': pdf_link or detail_link,
                'real_pdf': pdf_link or detail_link,
                'doi': doi,
                'source': 'DOAJ',
                'source_icon': '📖'
            }
            
        except Exception:
            return None
    
    def _clean_results(self, results, query):
        """Sonuçları temizle ve sırala"""
        seen_titles = set()
        unique_results = []
        
        for article in results:
            title = article.get('title', '').lower().strip()
            
            # Çok kısa başlıkları filtrele
            if len(title) < 10:
                continue
            
            # Tekrar edenleri filtrele
            if title in seen_titles:
                continue
            
            # Relevance kontrolü
            query_words = query.lower().split()
            title_words = title.split()
            
            # En az bir kelime eşleşmesi olmalı
            has_match = any(
                any(q_word in t_word for t_word in title_words)
                for q_word in query_words
            )
            
            if has_match:
                seen_titles.add(title)
                unique_results.append(article)
        
        return unique_results
    
    def fetch_abstract_from_url(self, url):
        """URL'den özet çekme fonksiyonu"""
        try:
            print(f"📄 Özet çekiliyor: {url}")
            
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Dergipark özet çekme
                if 'dergipark.org.tr' in url:
                    return self._extract_dergipark_abstract(soup)
                
                # DOI/CrossRef özet çekme
                elif 'doi.org' in url:
                    return self._extract_doi_abstract(soup)
                
                # Genel özet çekme
                else:
                    return self._extract_general_abstract(soup)
                    
        except Exception as e:
            print(f"❌ Özet çekme hatası: {e}")
            return None
        
        return None
    
    def _extract_dergipark_abstract(self, soup):
        """Dergipark'tan özet çek"""
        try:
            # Dergipark'ta "Öz" başlığı altındaki içerik
            abstract_selectors = [
                'div.article-abstract-tr',
                'div.article-abstract',
                'div[id*="abstract"]',
                'div[class*="abstract"]',
                '.article-summary',
                '.abstract-content',
                'div:contains("Öz") + div',
                'p:contains("Öz") + p'
            ]
            
            for selector in abstract_selectors:
                if ':contains(' in selector:
                    # BeautifulSoup doesn't support :contains, use find instead
                    if 'Öz' in selector:
                        oz_element = soup.find(text=lambda text: text and 'Öz' in text)
                        if oz_element:
                            parent = oz_element.parent
                            if parent:
                                next_element = parent.find_next_sibling()
                                if next_element:
                                    abstract_text = next_element.get_text(strip=True)
                                    if len(abstract_text) > 50:
                                        return abstract_text[:500] + "..." if len(abstract_text) > 500 else abstract_text
                else:
                    element = soup.select_one(selector)
                    if element:
                        abstract_text = element.get_text(strip=True)
                        if len(abstract_text) > 50:
                            return abstract_text[:500] + "..." if len(abstract_text) > 500 else abstract_text
            
            # Alternatif: Tüm p tag'lerinde özet ara
            for p in soup.find_all('p'):
                text = p.get_text(strip=True)
                if len(text) > 100 and any(keyword in text.lower() for keyword in ['amaç', 'çalışma', 'araştırma', 'sonuç']):
                    return text[:500] + "..." if len(text) > 500 else text
                    
        except Exception as e:
            print(f"❌ Dergipark özet çekme hatası: {e}")
        
        return None
    
    def _extract_doi_abstract(self, soup):
        """DOI sayfasından özet çek"""
        try:
            abstract_selectors = [
                'div.abstractSection',
                'div.abstract',
                'section.abstract',
                '.article-abstract',
                '.abstract-content'
            ]
            
            for selector in abstract_selectors:
                element = soup.select_one(selector)
                if element:
                    abstract_text = element.get_text(strip=True)
                    if len(abstract_text) > 50:
                        return abstract_text[:500] + "..." if len(abstract_text) > 500 else abstract_text
                        
        except Exception as e:
            print(f"❌ DOI özet çekme hatası: {e}")
        
        return None
    
    def _extract_general_abstract(self, soup):
        """Genel özet çekme"""
        try:
            # Meta description
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc and meta_desc.get('content'):
                content = meta_desc['content'].strip()
                if len(content) > 50:
                    return content[:500] + "..." if len(content) > 500 else content
            
            # og:description
            og_desc = soup.find('meta', attrs={'property': 'og:description'})
            if og_desc and og_desc.get('content'):
                content = og_desc['content'].strip()
                if len(content) > 50:
                    return content[:500] + "..." if len(content) > 500 else content
                    
        except Exception as e:
            print(f"❌ Genel özet çekme hatası: {e}")
        
        return None


# Fallback için sample articles
def get_sample_articles(query, limit=20):
    """Sample articles döndür"""
    current_year = datetime.now().year
    
    articles = [
        {
            'id': 'sample_1',
            'title': f'{query.title()} Konusunda Akademik Araştırma',
            'authors': 'Prof. Dr. Akademik Araştırmacı',
            'journal': 'International Journal of Research',
            'year': str(current_year),
            'abstract': f'Bu çalışma {query} konusunda yapılan güncel akademik araştırmaları incelemektedir.',
            'detail_link': 'https://example.com/research',
            'pdf_link': 'https://www.mevzuat.gov.tr/File/GeneratePdf?mevzuatNo=4721&mevzuatTur=1&mevzuatTertip=5',
            'real_pdf': 'https://www.mevzuat.gov.tr/File/GeneratePdf?mevzuatNo=4721&mevzuatTur=1&mevzuatTertip=5',
            'doi': '',
            'source': 'Academic Database',
            'source_icon': '📚'
        },
        {
            'id': 'sample_2',
            'title': f'{query.title()} Alanında Literatür Taraması',
            'authors': 'Doç. Dr. Literatür Uzmanı',
            'journal': 'Journal of Academic Studies',
            'year': str(current_year),
            'abstract': f'{query} alanında yapılan çalışmaların sistematik literatür taraması.',
            'detail_link': 'https://example.com/literature',
            'pdf_link': 'https://www.mevzuat.gov.tr/File/GeneratePdf?mevzuatNo=6102&mevzuatTur=1&mevzuatTertip=5',
            'real_pdf': 'https://www.mevzuat.gov.tr/File/GeneratePdf?mevzuatNo=6102&mevzuatTur=1&mevzuatTertip=5',
            'doi': '',
            'source': 'Academic Database',
            'source_icon': '📚'
        },
        {
            'id': 'sample_3',
            'title': f'Modern {query.title()} Yaklaşımları',
            'authors': 'Prof. Dr. Modern Yaklaşım Uzmanı',
            'journal': 'Contemporary Research Review',
            'year': str(current_year - 1),
            'abstract': f'{query} konusunda modern yaklaşımların ve güncel gelişmelerin analizi.',
            'detail_link': 'https://example.com/modern',
            'pdf_link': 'https://www.mevzuat.gov.tr/File/GeneratePdf?mevzuatNo=2004&mevzuatTur=1&mevzuatTertip=5',
            'real_pdf': 'https://www.mevzuat.gov.tr/File/GeneratePdf?mevzuatNo=2004&mevzuatTur=1&mevzuatTertip=5',
            'doi': '',
            'source': 'Academic Database',
            'source_icon': '📚'
        }
    ]
    
    return articles[:limit]