import requests
import re
from urllib.parse import urljoin, urlparse
import logging
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class SmartPDFLinkFinder:
    """
    Makale için PDF linklerini bulur - hibrit yaklaşım + Entegre DergiPark desteği
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'tr-TR,tr;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
    
    def find_pdf_links(self, article_data):
        """
        Makale için mevcut tüm PDF linklerini bul
        """
        results = {
            'pdf_links': [],
            'original_url': None,
            'doi_url': None,
            'has_pdf': False,
            'error': None
        }
        
        try:
            # Mevcut linkleri al
            doi = article_data.get('doi')
            doi_url = article_data.get('doi_url')
            url = article_data.get('url')
            title = article_data.get('title', '')
            source = article_data.get('source', '').lower()
            
            results['original_url'] = doi_url or url
            results['doi_url'] = doi_url
            
            print(f"🔍 PDF finder başladı - Source: {source}, DOI: {doi}")
            
            # 1. DergiPark özel kontrolü (yüksek öncelik) - Entegre!
            is_dergipark = (
                'dergipark' in source or 
                (url and 'dergipark.org.tr' in url) or
                (doi and self._is_dergipark_doi(doi))
            )
            
            if is_dergipark:
                print(f"📚 DergiPark makalesi algılandı! Entegre arama başlatılıyor...")
                dergipark_pdfs = self._comprehensive_dergipark_search(url, title, article_data, doi)
                results['pdf_links'].extend(dergipark_pdfs)
                print(f"📚 DergiPark'tan {len(dergipark_pdfs)} PDF bulundu")
            
            # 2. Doğrudan PDF link kontrolü
            if url and url.lower().endswith('.pdf'):
                results['pdf_links'].append({
                    'url': url,
                    'type': 'direct',
                    'source': 'Direct Link',
                    'quality': 'high'
                })
                print(f"📄 Doğrudan PDF linki bulundu")
            
            # 3. arXiv kontrolü
            if doi and 'arxiv' in doi.lower():
                arxiv_id = self._extract_arxiv_id(doi)
                if arxiv_id:
                    pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
                    results['pdf_links'].append({
                        'url': pdf_url,
                        'type': 'arxiv',
                        'source': 'arXiv',
                        'quality': 'high'
                    })
                    print(f"📖 arXiv PDF bulundu")
            
            # 4. PubMed Central kontrolü
            if doi:
                pmc_pdf = self._check_pmc_pdf(doi)
                if pmc_pdf:
                    results['pdf_links'].append({
                        'url': pmc_pdf,
                        'type': 'pmc',
                        'source': 'PubMed Central',
                        'quality': 'high'
                    })
                    print(f"🏥 PubMed Central PDF bulundu")
            
            # 5. DOI sayfası tarama (dikkatli)
            if doi_url and len(results['pdf_links']) == 0:
                scraped_pdfs = self._scrape_pdf_from_doi(doi_url)
                results['pdf_links'].extend(scraped_pdfs)
                if scraped_pdfs:
                    print(f"🔍 DOI scraping ile {len(scraped_pdfs)} PDF bulundu")
            
            # 6. CrossRef API'den ek bilgi
            if doi and len(results['pdf_links']) == 0:
                crossref_pdf = self._check_crossref_pdf(doi)
                if crossref_pdf:
                    results['pdf_links'].append(crossref_pdf)
                    print(f"🔗 CrossRef PDF bulundu")
            
            # 7. Alternatif kaynaklar
            if title and len(results['pdf_links']) == 0:
                alt_pdfs = self._check_alternative_sources(title)
                results['pdf_links'].extend(alt_pdfs)
                if alt_pdfs:
                    print(f"🌐 Alternatif kaynaklardan {len(alt_pdfs)} PDF bulundu")
            
            results['has_pdf'] = len(results['pdf_links']) > 0
            print(f"✅ Toplam {len(results['pdf_links'])} PDF bulundu")
            
        except Exception as e:
            logger.error(f"PDF link finding error: {e}")
            results['error'] = str(e)
            print(f"❌ PDF arama hatası: {e}")
        
        return results
    
    def _is_dergipark_doi(self, doi):
        """
        DOI'nin DergiPark'a ait olup olmadığını kontrol et
        """
        dergipark_patterns = [
            r'10\.32331/',  # TÜBİTAK dergileri
            r'10\.26466/',  # Diğer DergiPark dergileri
            r'10\.16953/',  # Akademik dergileri
            r'10\.24014/',  # Yeni DergiPark dergileri
            r'10\.53461/',  # 2021+ dergileri
            r'10\.38155/',  # Yeni sistemler
            r'10\.21565/',  # Özel Eğitim dergileri
            r'10\.17152/',  # GEFAD dergileri
            r'10\.29065/',  # USAKEAD dergileri
            r'10\.1501/',   # Eski sistem dergileri
            r'10\.29329/',  # MJER dergileri
        ]
        
        return any(re.search(pattern, doi) for pattern in dergipark_patterns)
    
    def _comprehensive_dergipark_search(self, url, title, article_data, doi):
        """
        Kapsamlı DergiPark PDF arama - Entegre versiyon
        """
        pdf_links = []
        
        try:
            # DergiPark URL'ini oluştur/bul
            dergipark_url = self._construct_dergipark_url(url, doi, title)
            
            if dergipark_url:
                print(f"📚 DergiPark URL: {dergipark_url}")
                
                # DergiPark sayfasını getir
                response = self.session.get(dergipark_url, timeout=15)
                print(f"📚 DergiPark yanıt: {response.status_code}")
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Çoklu PDF arama stratejileri
                    pdf_links = self._multi_strategy_pdf_search(soup, dergipark_url)
                    
                    print(f"📚 Toplam {len(pdf_links)} PDF bulundu")
                    
                else:
                    print(f"📚 DergiPark sayfası erişilemez: {response.status_code}")
            
            # URL bulunamazsa başlık ile arama
            if not pdf_links and title and len(title) > 10:
                print(f"📚 Başlık ile DergiPark araması yapılıyor...")
                search_results = self._search_dergipark_by_title(title)
                pdf_links.extend(search_results)
        
        except Exception as e:
            print(f"📚 DergiPark arama hatası: {e}")
            logger.debug(f"DergiPark search error: {e}")
        
        return pdf_links[:3]  # Maksimum 3 PDF
    
    def _construct_dergipark_url(self, url, doi, title):
        """
        DergiPark URL'ini oluştur
        """
        # Mevcut URL varsa kullan
        if url and 'dergipark.org.tr' in url:
            return url
        
        # DOI'den URL oluştur
        if doi:
            # Bilinen DergiPark DOI patternleri
            doi_patterns = [
                # Sosyal Güvenlik Dergisi
                (r'10\.32331/sgd\.(\d+)', r'https://dergipark.org.tr/tr/pub/sgd/article/\1'),
                # Özel Eğitim Dergisi
                (r'10\.21565/ozelegitimdergisi\.(\d+)', r'https://dergipark.org.tr/tr/pub/ozelegitimdergisi/article/\1'),
                # GEFAD
                (r'10\.17152/gefad\.(\d+)', r'https://dergipark.org.tr/tr/pub/gefad/article/\1'),
                # USAKEAD
                (r'10\.29065/usakead\.(\d+)', r'https://dergipark.org.tr/tr/pub/usakead/article/\1'),
                # MJER
                (r'10\.29329/mjer\.(\d+)', r'https://dergipark.org.tr/tr/pub/mjer/article/\1'),
                # Genel 10.32331 pattern (TÜBİTAK dergileri)
                (r'10\.32331/([^.]+)\.(\d+)', r'https://dergipark.org.tr/tr/pub/\1/article/\2'),
                # Genel 10.21565 pattern
                (r'10\.21565/([^.]+)\.(\d+)', r'https://dergipark.org.tr/tr/pub/\1/article/\2'),
                # Genel 10.17152 pattern
                (r'10\.17152/([^.]+)\.(\d+)', r'https://dergipark.org.tr/tr/pub/\1/article/\2'),
                # Genel 10.29065 pattern
                (r'10\.29065/([^.]+)\.(\d+)', r'https://dergipark.org.tr/tr/pub/\1/article/\2'),
                # Genel 10.29329 pattern
                (r'10\.29329/([^.]+)\.(\d+)', r'https://dergipark.org.tr/tr/pub/\1/article/\2'),
                # 10.26466 pattern
                (r'10\.26466/([^.]+)\.(\d+)', r'https://dergipark.org.tr/tr/pub/\1/article/\2'),
                # 10.16953 pattern
                (r'10\.16953/([^.]+)\.(\d+)', r'https://dergipark.org.tr/tr/pub/\1/article/\2'),
                # 10.24014 pattern
                (r'10\.24014/([^.]+)\.(\d+)', r'https://dergipark.org.tr/tr/pub/\1/article/\2'),
                # 10.1501 pattern
                (r'10\.1501/([^.]+)\.(\d+)', r'https://dergipark.org.tr/tr/pub/\1/article/\2'),
                # Genel DergiPark pattern
                (r'10\.\d+/([^.]+)\.(\d+)', r'https://dergipark.org.tr/tr/pub/\1/article/\2'),
            ]
            
            for pattern, replacement in doi_patterns:
                match = re.search(pattern, doi)
                if match:
                    url = re.sub(pattern, replacement, doi)
                    print(f"📚 DOI'den URL oluşturuldu: {doi} -> {url}")
                    return url
        
        return None
    
    def _multi_strategy_pdf_search(self, soup, base_url):
        """
        Çoklu strateji ile PDF arama
        """
        pdf_links = []
        
        # Strateji 1: "Makale Dosyaları" bölümü arama
        print(f"📚 Strateji 1: Makale Dosyaları bölümü aranıyor...")
        pdf_links.extend(self._search_article_files_section(soup, base_url))
        
        # Strateji 2: "Tam Metin" direkt arama
        if not pdf_links:
            print(f"📚 Strateji 2: Tam Metin linkleri aranıyor...")
            pdf_links.extend(self._search_full_text_links(soup, base_url))
        
        # Strateji 3: Download pattern arama
        if not pdf_links:
            print(f"📚 Strateji 3: Download pattern aranıyor...")
            pdf_links.extend(self._search_download_patterns(soup, base_url))
        
        # Strateji 4: Right sidebar arama
        if not pdf_links:
            print(f"📚 Strateji 4: Right sidebar aranıyor...")
            pdf_links.extend(self._search_right_sidebar(soup, base_url))
        
        # Strateji 5: Genel PDF link arama
        if not pdf_links:
            print(f"📚 Strateji 5: Genel PDF linkler aranıyor...")
            pdf_links.extend(self._search_general_pdf_links(soup, base_url))
        
        return pdf_links
    
    def _search_article_files_section(self, soup, base_url):
        """
        "Makale Dosyaları" bölümünü arama
        """
        pdf_links = []
        
        # Makale dosyaları başlık arama
        file_section_texts = [
            'Makale Dosyaları', 'Article Files', 'Dosyalar', 'Files',
            'Tam Metin', 'Full Text', 'PDF', 'İndir', 'Download'
        ]
        
        for section_text in file_section_texts:
            # Section başlığını bul
            sections = soup.find_all(string=re.compile(section_text, re.IGNORECASE))
            print(f"📚 '{section_text}' için {len(sections)} bölüm bulundu")
            
            for section in sections:
                parent = section.find_parent()
                if parent:
                    # Bu section'ın altındaki linkler
                    download_links = self._find_download_links_in_parent(parent)
                    
                    for link_info in download_links:
                        pdf_url = self._make_absolute_url(link_info['url'], base_url)
                        pdf_links.append({
                            'url': pdf_url,
                            'type': f'section_{section_text.lower().replace(" ", "_")}',
                            'source': 'DergiPark',
                            'quality': 'high',
                            'found_method': f'Section: {section_text}'
                        })
                        print(f"📚 Section PDF bulundu ({section_text}): {pdf_url}")
                    
                    if download_links:
                        break
            
            if pdf_links:
                break
        
        return pdf_links[:2]
    
    def _search_full_text_links(self, soup, base_url):
        """
        "Tam Metin" direkt link arama
        """
        pdf_links = []
        
        # Tam metin link arama
        full_text_patterns = [
            r'Tam\s+Metin', r'Full\s+Text', r'PDF\s+İndir', r'Download\s+PDF',
            r'Makale\s+PDF', r'Article\s+PDF', r'İndir', r'Download'
        ]
        
        for pattern in full_text_patterns:
            links = soup.find_all('a', string=re.compile(pattern, re.IGNORECASE))
            print(f"📚 '{pattern}' için {len(links)} link bulundu")
            
            for link in links:
                href = link.get('href')
                if href and self._is_pdf_link(href):
                    pdf_url = self._make_absolute_url(href, base_url)
                    
                    pdf_links.append({
                        'url': pdf_url,
                        'type': 'full_text_direct',
                        'source': 'DergiPark',
                        'quality': 'high',
                        'found_method': f'Direct text: {pattern}'
                    })
                    print(f"📚 Tam Metin PDF bulundu: {pdf_url}")
                    break
            
            if pdf_links:
                break
        
        return pdf_links[:1]
    
    def _search_download_patterns(self, soup, base_url):
        """
        Download pattern arama
        """
        pdf_links = []
        
        # Download URL patternleri
        download_patterns = [
            r'/download/article-file/\d+',
            r'/download/[^/]+/\d+',
            r'/tr/download/[^"\']*',
            r'/en/download/[^"\']*',
        ]
        
        for pattern in download_patterns:
            links = soup.find_all('a', href=re.compile(pattern))
            print(f"📚 Pattern '{pattern}' için {len(links)} link bulundu")
            
            for link in links[:3]:  # İlk 3 link
                href = link.get('href')
                if href:
                    pdf_url = self._make_absolute_url(href, base_url)
                    
                    pdf_links.append({
                        'url': pdf_url,
                        'type': 'download_pattern',
                        'source': 'DergiPark',
                        'quality': 'high',
                        'found_method': f'Pattern: {pattern}'
                    })
                    print(f"📚 Pattern PDF bulundu: {pdf_url}")
                    
                    if len(pdf_links) >= 2:
                        break
            
            if pdf_links:
                break
        
        return pdf_links[:2]
    
    def _search_right_sidebar(self, soup, base_url):
        """
        Right sidebar arama
        """
        pdf_links = []
        
        # Right sidebar sınıfları
        sidebar_selectors = [
            '.journal_panel_menu', '.right-panel', '.sidebar-right',
            '.article-sidebar', '.journal-sidebar', '.kt-portlet'
        ]
        
        for selector in sidebar_selectors:
            sidebars = soup.select(selector)
            print(f"📚 Selector '{selector}' için {len(sidebars)} sidebar bulundu")
            
            for sidebar in sidebars:
                download_links = self._find_download_links_in_parent(sidebar)
                
                for link_info in download_links:
                    pdf_url = self._make_absolute_url(link_info['url'], base_url)
                    pdf_links.append({
                        'url': pdf_url,
                        'type': 'sidebar',
                        'source': 'DergiPark',
                        'quality': 'high',
                        'found_method': f'Sidebar: {selector}'
                    })
                    print(f"📚 Sidebar PDF bulundu: {pdf_url}")
                
                if download_links:
                    break
            
            if pdf_links:
                break
        
        return pdf_links[:2]
    
    def _search_general_pdf_links(self, soup, base_url):
        """
        Genel PDF link arama
        """
        pdf_links = []
        
        # Genel PDF içeren linkler
        all_links = soup.find_all('a', href=True)
        print(f"📚 Toplam {len(all_links)} link kontrol ediliyor")
        
        pdf_count = 0
        for link in all_links:
            href = link.get('href')
            link_text = link.get_text(strip=True).lower()
            
            # PDF belirten keywords
            pdf_keywords = ['pdf', 'tam metin', 'full text', 'download', 'indir', 'makale']
            
            if (self._is_pdf_link(href) or 
                any(keyword in link_text for keyword in pdf_keywords)):
                
                if self._is_pdf_link(href):
                    pdf_url = self._make_absolute_url(href, base_url)
                    
                    pdf_links.append({
                        'url': pdf_url,
                        'type': 'general_search',
                        'source': 'DergiPark',
                        'quality': 'medium',
                        'found_method': f'General: {link_text[:20]}...'
                    })
                    print(f"📚 Genel PDF bulundu: {pdf_url}")
                    pdf_count += 1
                    
                    if pdf_count >= 3:
                        break
        
        return pdf_links[:3]
    
    def _find_download_links_in_parent(self, parent):
        """
        Parent element içinde download linklerini bul
        """
        download_links = []
        
        # Download linki patternleri
        download_selectors = [
            'a[href*="/download/"]',
            'a[href*="article-file"]',
            'a[href*=".pdf"]',
        ]
        
        for selector in download_selectors:
            links = parent.select(selector)
            
            for link in links[:2]:  # İlk 2 link
                href = link.get('href')
                if href and self._is_pdf_link(href):
                    download_links.append({
                        'url': href,
                        'text': link.get_text(strip=True)
                    })
        
        return download_links
    
    def _is_pdf_link(self, href):
        """
        Link'in PDF olup olmadığını kontrol et
        """
        if not href:
            return False
        
        href_lower = href.lower()
        
        # PDF belirten patternler
        pdf_indicators = [
            '/download/article-file/',
            '/download/',
            '.pdf',
            'pdf',
            'article-file'
        ]
        
        return any(indicator in href_lower for indicator in pdf_indicators)
    
    def _make_absolute_url(self, href, base_url):
        """
        Relative URL'yi absolute yap
        """
        if href.startswith('/'):
            return 'https://dergipark.org.tr' + href
        elif href.startswith('http'):
            return href
        else:
            return urljoin(base_url, href)
    
    def _search_dergipark_by_title(self, title):
        """
        Başlık ile DergiPark arama
        """
        pdf_links = []
        
        try:
            search_url = "https://dergipark.org.tr/tr/search"
            params = {
                'q': title[:100],
                'section': 'articles'
            }
            
            response = self.session.get(search_url, params=params, timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # İlk makale linklerini bul
                article_links = soup.find_all('a', href=re.compile(r'/tr/pub/[^/]+/article/\d+'))
                print(f"📚 Başlık aramasında {len(article_links)} makale bulundu")
                
                for article_link in article_links[:2]:  # İlk 2 sonuç
                    article_url = 'https://dergipark.org.tr' + article_link['href']
                    print(f"📚 Arama sonucu makale: {article_url}")
                    
                    # Bu makale sayfasından PDF çek (recursion'dan kaçınmak için basit arama)
                    simple_pdfs = self._simple_dergipark_pdf_extract(article_url)
                    pdf_links.extend(simple_pdfs)
                    
                    if pdf_links:
                        break
        
        except Exception as e:
            print(f"📚 Başlık arama hatası: {e}")
        
        return pdf_links
    
    def _simple_dergipark_pdf_extract(self, url):
        """
        Basit DergiPark PDF çıkarma (recursion önlemek için)
        """
        pdf_links = []
        
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Sadece download pattern ara
                download_links = soup.find_all('a', href=re.compile(r'/download/article-file/\d+'))
                
                for link in download_links[:1]:  # Sadece ilk link
                    href = link.get('href')
                    if href:
                        pdf_url = self._make_absolute_url(href, url)
                        pdf_links.append({
                            'url': pdf_url,
                            'type': 'search_result',
                            'source': 'DergiPark',
                            'quality': 'high',
                            'found_method': 'Title search'
                        })
                        print(f"📚 Arama sonucu PDF: {pdf_url}")
        
        except Exception as e:
            print(f"📚 Basit PDF çıkarma hatası: {e}")
        
        return pdf_links
    
    def _extract_arxiv_id(self, doi):
        """arXiv ID çıkar"""
        patterns = [
            r'arxiv[:/](\d+\.\d+)',
            r'(\d{4}\.\d{4,5})',
            r'arXiv:(\d+\.\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, doi, re.IGNORECASE)
            if match:
                return match.group(1)
        return None
    
    def _check_pmc_pdf(self, doi):
        """PubMed Central PDF kontrolü"""
        try:
            pmc_search_url = f"https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/?ids={doi}&format=json"
            response = self.session.get(pmc_search_url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                records = data.get('records', [])
                
                for record in records:
                    pmcid = record.get('pmcid')
                    if pmcid:
                        pdf_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/pdf/"
                        return pdf_url
        
        except Exception as e:
            logger.debug(f"PMC check error: {e}")
        
        return None
    
    def _scrape_pdf_from_doi(self, doi_url):
        """DOI sayfasından PDF linklerini bul"""
        pdf_links = []
        
        try:
            trusted_domains = ['springer.com', 'wiley.com', 'elsevier.com', 'nature.com', 'science.org']
            domain = urlparse(doi_url).netloc.lower()
            
            if not any(trusted in domain for trusted in trusted_domains):
                return pdf_links
            
            response = self.session.get(doi_url, timeout=15)
            if response.status_code != 200:
                return pdf_links
            
            content = response.text
            pdf_patterns = [
                r'href=["\']([^"\']*\.pdf[^"\']*)["\']',
                r'data-pdf-url=["\']([^"\']*)["\']',
                r'"pdfUrl":\s*"([^"]*)"',
            ]
            
            for pattern in pdf_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    if match.startswith('/'):
                        match = urljoin(doi_url, match)
                    elif match.startswith('http'):
                        pass
                    else:
                        continue
                    
                    pdf_links.append({
                        'url': match,
                        'type': 'scraped',
                        'source': domain,
                        'quality': 'medium'
                    })
                    break
                
                if pdf_links:
                    break
        
        except Exception as e:
            logger.debug(f"DOI scraping error: {e}")
        
        return pdf_links[:1]
    
    def _check_crossref_pdf(self, doi):
        """CrossRef API'den PDF link kontrolü"""
        try:
            crossref_url = f"https://api.crossref.org/works/{doi}"
            response = self.session.get(crossref_url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                work = data.get('message', {})
                
                links = work.get('link', [])
                for link in links:
                    if link.get('content-type') == 'application/pdf':
                        return {
                            'url': link.get('URL'),
                            'type': 'crossref',
                            'source': 'CrossRef',
                            'quality': 'high'
                        }
        
        except Exception as e:
            logger.debug(f"CrossRef PDF check error: {e}")
        
        return None
    
    def _check_alternative_sources(self, title):
        """Alternatif kaynaklardan PDF ara"""
        alt_pdfs = []
        
        try:
            if len(title) > 10:
                doaj_results = self._search_doaj(title)
                alt_pdfs.extend(doaj_results)
        
        except Exception as e:
            logger.debug(f"Alternative source error: {e}")
        
        return alt_pdfs[:2]
    
    def _search_doaj(self, title):
        """DOAJ'dan açık erişim PDF ara"""
        try:
            doaj_url = "https://doaj.org/api/v2/search/articles/"
            params = {
                'query': title[:100],
                'pageSize': 3
            }
            
            response = self.session.get(doaj_url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                
                pdfs = []
                for result in results:
                    bibjson = result.get('bibjson', {})
                    links = bibjson.get('link', [])
                    
                    for link in links:
                        if link.get('type') == 'fulltext' and 'pdf' in link.get('content_type', '').lower():
                            pdfs.append({
                                'url': link.get('url'),
                                'type': 'doaj',
                                'source': 'DOAJ (Open Access)',
                                'quality': 'medium'
                            })
                            break
                
                return pdfs[:1]
        
        except Exception as e:
            logger.debug(f"DOAJ search error: {e}")
        
        return []

def find_article_pdf_links(article_data):
    """
    Ana fonksiyon - makale için PDF linklerini bul
    """
    finder = SmartPDFLinkFinder()
    return finder.find_pdf_links(article_data)