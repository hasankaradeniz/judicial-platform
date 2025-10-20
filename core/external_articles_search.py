# core/external_articles_search.py

import requests
from bs4 import BeautifulSoup
import re
import time
from urllib.parse import quote, urljoin
from django.core.cache import cache
import hashlib


class ExternalArticleSearcher:
    """Harici kaynaklardan makale arama sınıfı - Sadece gerçek API'ler"""
    
    def __init__(self):
        self.session = requests.Session()
        self.current_proxy = None
        self._setup_session()
        
    def _setup_session(self):
        """Session kurulumu ve proxy rotation"""
        # Çeşitli User-Agent'lar
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15'
        ]
        
        selected_agent = random.choice(user_agents)
        
        # Daha gelişmiş ve güncel headers
        self.session.headers.update({
            'User-Agent': selected_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'tr-TR,tr;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0'
        })
        
        print(f"Session başlatıldı - User-Agent: {selected_agent[:50]}...")
    
    def search_all_sources(self, query, limit=20):
        """Sadece gerçek akademik makale arama - simülasyon yok"""
        cache_key = f'external_articles_{hashlib.md5(query.encode()).hexdigest()}'
        cached_result = cache.get(cache_key)
        
        if cached_result:
            return cached_result
        
        results = []
        
        # 1. CrossRef API - Rate limiting ile
        try:
            time.sleep(random.uniform(1, 3))  # Request arası bekleme
            crossref_results = self.search_crossref(query, limit)
            if crossref_results:
                results.extend(crossref_results)
                print(f"CrossRef'den {len(crossref_results)} sonuç bulundu")
        except Exception as e:
            print(f"CrossRef API hatası: {e}")
            
        # 2. DOAJ API - Rate limiting ile
        try:
            time.sleep(random.uniform(2, 4))  # Request arası bekleme
            doaj_results = self.search_doaj(query, limit)
            if doaj_results:
                results.extend(doaj_results)
                print(f"DOAJ'dan {len(doaj_results)} sonuç bulundu")
        except Exception as e:
            print(f"DOAJ API hatası: {e}")
            
        # 3. PubMed/PMC API (Tıp makaleleri için)
        try:
            time.sleep(random.uniform(1, 2))  # Request arası bekleme
            pubmed_results = self.search_pubmed(query, min(limit//3, 10))
            if pubmed_results:
                results.extend(pubmed_results)
                print(f"PubMed'den {len(pubmed_results)} sonuç bulundu")
        except Exception as e:
            print(f"PubMed API hatası: {e}")
            
        # 4. IEEE Xplore API (Teknik makaleler için) - Daha az agresif
        try:
            time.sleep(random.uniform(2, 5))  # Request arası bekleme
            ieee_results = self.search_ieee(query, min(limit//4, 5))
            if ieee_results:
                results.extend(ieee_results)
                print(f"IEEE'den {len(ieee_results)} sonuç bulundu")
        except Exception as e:
            print(f"IEEE API hatası: {e}")
        
        # Sonuçları relevance'a göre filtrele ve benzersiz hale getir
        seen_titles = set()
        unique_results = []
        for article in results:
            title = article.get('title', '').lower().strip()
            if title and title not in seen_titles and len(title) > 10:
                # Başlık relevance kontrolü - arama terimini içeriyor mu?
                query_lower = query.lower()
                title_lower = title.lower()
                
                # Tam eşleşme veya önemli kelime eşleşmesi
                query_words = query_lower.split()
                title_words = title_lower.split()
                
                # En az arama kelimelerinin %50'si başlıkta olmalı
                matching_words = sum(1 for word in query_words if any(word in title_word for title_word in title_words))
                relevance_score = matching_words / len(query_words) if query_words else 0
                
                if relevance_score >= 0.3:  # En az %30 eşleşme
                    seen_titles.add(title)
                    article['relevance_score'] = relevance_score
                    unique_results.append(article)
        
        # Relevance score'a göre sırala
        unique_results.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        
        # Her makaleye benzersiz ID ekle
        for i, article in enumerate(unique_results):
            if not article.get('id'):
                source = article.get('source', 'unknown').lower()
                title_hash = hash(article.get('title', '')) % 100000
                article['id'] = f"{source}_{title_hash}_{i}"
        
        print(f"Toplam {len(unique_results)} benzersiz makale bulundu")
        
        # Cache'e kaydet (1 saat)
        cache.set(cache_key, unique_results, 3600)
        
        return unique_results
    
    def search_crossref(self, query, limit=10):
        """CrossRef API ile akademik makale arama - ana kaynak"""
        results = []
        try:
            # CrossRef REST API - sadece başlık araması
            search_url = "https://api.crossref.org/works"
            params = {
                'query.title': query,  # Sadece başlıkta ara
                'rows': limit,
                'sort': 'score',  # Relevance score'a göre sırala
                'order': 'desc',
                'filter': 'has-full-text:true,type:journal-article'  # Sadece dergi makaleleri
            }
            
            response = self.session.get(search_url, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                if 'message' in data and 'items' in data['message']:
                    for item in data['message']['items']:
                        result = self.parse_crossref_article(item)
                        if result:
                            result['source'] = 'CrossRef'
                            result['source_icon'] = '🔬'
                            results.append(result)
                            
        except Exception as e:
            print(f"CrossRef API hatası: {e}")
        
        return results
    
    def search_doaj(self, query, limit=10):
        """DOAJ API ile açık erişim dergi makalesi arama - ana kaynak"""
        results = []
        try:
            # DOAJ API - sadece başlık araması
            search_url = "https://doaj.org/api/search/articles"
            params = {
                'query': f'bibjson.title:"{query}"',  # Sadece başlıkta ara
                'pageSize': limit,
                'sort': 'score:desc'  # Relevance score'a göre
            }
            
            response = self.session.get(search_url, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                if 'results' in data:
                    for item in data['results']:
                        result = self.parse_doaj_article(item)
                        if result:
                            result['source'] = 'DOAJ'
                            result['source_icon'] = '📖'
                            results.append(result)
                            
        except Exception as e:
            print(f"DOAJ API hatası: {e}")
        
        return results
    
    def search_pubmed(self, query, limit=10):
        """PubMed/PMC API ile tıp makaleleri arama"""
        results = []
        try:
            # PubMed eSearch API - sadece başlık araması
            search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
            params = {
                'db': 'pubmed',
                'term': f'"{query}"[Title]',  # Sadece başlıkta ara
                'retmax': limit,
                'retmode': 'json',
                'sort': 'relevance'
            }
            
            response = self.session.get(search_url, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                if 'esearchresult' in data and 'idlist' in data['esearchresult']:
                    pmids = data['esearchresult']['idlist']
                    
                    # Her PMID için detay bilgilerini al
                    if pmids:
                        detail_results = self._get_pubmed_details(pmids[:limit])
                        results.extend(detail_results)
                        
        except Exception as e:
            print(f"PubMed API hatası: {e}")
        
        return results
    
    def _get_pubmed_details(self, pmids):
        """PubMed makale detaylarını al"""
        results = []
        try:
            # PMC eFetch API
            detail_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
            params = {
                'db': 'pubmed',
                'id': ','.join(pmids),
                'retmode': 'xml'
            }
            
            response = self.session.get(detail_url, params=params, timeout=20)
            if response.status_code == 200:
                import xml.etree.ElementTree as ET
                root = ET.fromstring(response.content)
                
                for article in root.findall('.//PubmedArticle'):
                    try:
                        result = self._parse_pubmed_article(article)
                        if result:
                            result['source'] = 'PubMed'
                            result['source_icon'] = '🏥'
                            results.append(result)
                    except Exception as e:
                        continue
                        
        except Exception as e:
            print(f"PubMed detay alma hatası: {e}")
        
        return results
    
    def _parse_pubmed_article(self, article):
        """PubMed makale XML'ini parse et"""
        try:
            # Başlık
            title_elem = article.find('.//ArticleTitle')
            title = title_elem.text if title_elem is not None else 'Başlık bulunamadı'
            
            # Yazarlar
            authors = []
            for author in article.findall('.//Author'):
                lastname = author.find('LastName')
                forename = author.find('ForeName')
                if lastname is not None and forename is not None:
                    authors.append(f"{forename.text} {lastname.text}")
            authors_str = ', '.join(authors) if authors else 'Yazar bilgisi yok'
            
            # Dergi
            journal_elem = article.find('.//Journal/Title')
            journal = journal_elem.text if journal_elem is not None else 'Dergi bilgisi yok'
            
            # Yıl
            year_elem = article.find('.//PubDate/Year')
            year = year_elem.text if year_elem is not None else ''
            
            # PMID
            pmid_elem = article.find('.//PMID')
            pmid = pmid_elem.text if pmid_elem is not None else ''
            
            # DOI
            doi = ''
            for elocation in article.findall('.//ELocationID'):
                if elocation.get('EIdType') == 'doi':
                    doi = elocation.text
                    break
            
            # Özet
            abstract_elem = article.find('.//Abstract/AbstractText')
            abstract = abstract_elem.text if abstract_elem is not None else 'Özet mevcut değil'
            if len(abstract) > 300:
                abstract = abstract[:300] + "..."
            
            # Linkler
            detail_link = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else ''
            pdf_link = f"https://doi.org/{doi}" if doi else detail_link
            
            return {
                'id': f"pubmed_{pmid}" if pmid else f"pubmed_{hash(title)%100000}",
                'title': title,
                'authors': authors_str,
                'journal': journal,
                'year': year,
                'abstract': abstract,
                'detail_link': detail_link,
                'pdf_link': pdf_link,
                'real_pdf': pdf_link,
                'doi': doi
            }
            
        except Exception as e:
            return None
    
    def search_ieee(self, query, limit=5):
        """IEEE Xplore API ile teknik makale arama"""
        results = []
        try:
            # IEEE Xplore API - sadece başlık araması
            search_url = "http://ieeexploreapi.ieee.org/api/v1/search/articles"
            params = {
                'article_title': query,  # Sadece başlıkta ara
                'max_records': limit,
                'start_record': 1,
                'sort_order': 'desc',
                'sort_field': 'relevance'  # Relevance'a göre sırala
            }
            
            response = self.session.get(search_url, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                if 'articles' in data:
                    for item in data['articles']:
                        result = self._parse_ieee_article(item)
                        if result:
                            result['source'] = 'IEEE'
                            result['source_icon'] = '⚡'
                            results.append(result)
                            
        except Exception as e:
            print(f"IEEE API hatası: {e}")
        
        return results
    
    def _parse_ieee_article(self, item):
        """IEEE makale verisini parse et"""
        try:
            title = item.get('title', 'Başlık bulunamadı')
            
            # Yazarlar
            authors = []
            if item.get('authors', {}).get('authors'):
                for author in item['authors']['authors']:
                    full_name = author.get('full_name', '')
                    if full_name:
                        authors.append(full_name)
            authors_str = ', '.join(authors) if authors else 'Yazar bilgisi yok'
            
            # Dergi/Konferans
            journal = item.get('publication_title', 'Yayın bilgisi yok')
            
            # Yıl
            year = str(item.get('publication_year', ''))
            
            # DOI ve linkler
            doi = item.get('doi', '')
            detail_link = f"https://doi.org/{doi}" if doi else item.get('html_url', '')
            pdf_link = item.get('pdf_url', '') or detail_link
            
            # Özet
            abstract = item.get('abstract', 'Özet mevcut değil')
            if len(abstract) > 300:
                abstract = abstract[:300] + "..."
            
            return {
                'id': f"ieee_{doi.replace('/', '_')}" if doi else f"ieee_{hash(title)%100000}",
                'title': title,
                'authors': authors_str,
                'journal': journal,
                'year': year,
                'abstract': abstract,
                'detail_link': detail_link,
                'pdf_link': pdf_link,
                'real_pdf': pdf_link,
                'doi': doi
            }
            
        except Exception as e:
            return None
    
    def parse_crossref_article(self, item):
        """CrossRef makale verisini parse et"""
        try:
            title = item.get('title', ['Başlık bulunamadı'])[0] if item.get('title') else 'Başlık bulunamadı'
            
            # Yazarlar
            authors = []
            if item.get('author'):
                for author in item['author']:
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
            
            # PDF linklerini bulmak için çeşitli yöntemler
            pdf_link = ''
            
            # 1. CrossRef'deki direkt PDF linkler
            if item.get('link'):
                for link in item['link']:
                    if link.get('content-type') == 'application/pdf':
                        pdf_link = link.get('URL', '')
                        break
                    elif 'pdf' in link.get('URL', '').lower():
                        pdf_link = link.get('URL', '')
                        break
            
            # 2. URL alanındaki PDF linkler
            if not pdf_link and item.get('URL'):
                url = item['URL']
                if 'pdf' in url.lower() or url.endswith('.pdf'):
                    pdf_link = url
            
            # 3. Fallback - DOI linkini PDF olarak kullan
            if not pdf_link:
                pdf_link = detail_link
            
            # Özet (varsa)
            abstract = item.get('abstract', 'Özet mevcut değil')
            if len(abstract) > 300:
                abstract = abstract[:300] + "..."
            
            return {
                'id': doi.replace('/', '_') if doi else f"crossref_{hash(title)%100000}",
                'title': title,
                'authors': authors_str,
                'journal': journal,
                'year': year,
                'abstract': abstract,
                'detail_link': detail_link,
                'pdf_link': pdf_link,
                'real_pdf': pdf_link,
                'doi': doi
            }
            
        except Exception as e:
            return None
    
    def parse_doaj_article(self, item):
        """DOAJ makale verisini parse et"""
        try:
            bibjson = item.get('bibjson', {})
            
            title = bibjson.get('title', 'Başlık bulunamadı')
            
            # Yazarlar
            authors = []
            if bibjson.get('author'):
                for author in bibjson['author']:
                    name = author.get('name', '')
                    if name:
                        authors.append(name)
            authors_str = ', '.join(authors) if authors else 'Yazar bilgisi yok'
            
            # Dergi
            journal = bibjson.get('journal', {}).get('title', 'Dergi bilgisi yok')
            
            # Yıl
            year = str(bibjson.get('year', ''))
            
            # DOI ve linkler
            doi = ''
            detail_link = ''
            pdf_link = ''
            
            # DOI bilgisi
            if bibjson.get('identifier'):
                for identifier in bibjson['identifier']:
                    if identifier.get('type') == 'doi':
                        doi = identifier.get('id', '')
                        detail_link = f"https://doi.org/{doi}"
                        break
            
            # PDF ve full-text linkler (DOAJ açık erişim odaklı)
            if bibjson.get('link'):
                for link in bibjson['link']:
                    link_type = link.get('type', '').lower()
                    url = link.get('url', '')
                    
                    # PDF link önceliği
                    if 'pdf' in link_type or 'pdf' in url.lower():
                        pdf_link = url
                        break
                    elif link_type == 'fulltext':
                        if not pdf_link:
                            pdf_link = url
                        if not detail_link:
                            detail_link = url
            
            # Son çare olarak detail link'i kullan
            if not pdf_link and detail_link:
                pdf_link = detail_link
            
            # Özet
            abstract = bibjson.get('abstract', 'Özet mevcut değil')
            if len(abstract) > 300:
                abstract = abstract[:300] + "..."
            
            return {
                'id': doi.replace('/', '_') if doi else f"doaj_{hash(title)%100000}",
                'title': title,
                'authors': authors_str,
                'journal': journal,
                'year': year,
                'abstract': abstract,
                'detail_link': detail_link or pdf_link,
                'pdf_link': pdf_link,
                'real_pdf': pdf_link,
                'doi': doi
            }
            
        except Exception as e:
            return None