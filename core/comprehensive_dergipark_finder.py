import requests
import re
from urllib.parse import urljoin, urlparse
import logging
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class ComprehensiveDergiParkFinder:
    """
    DergiPark için kapsamlı PDF bulma sistemi - tüm dergi formatlarını destekler
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
    
    def find_dergipark_pdfs(self, url, title, article_data, doi):
        """
        DergiPark'tan kapsamlı PDF arama
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
                    pdf_links = self._comprehensive_pdf_search(soup, dergipark_url)
                    
                    print(f"📚 Toplam {len(pdf_links)} PDF bulundu")
                    
                else:
                    print(f"📚 DergiPark sayfası erişilemez: {response.status_code}")
            
            # URL bulunamazsa başlık ile arama
            if not pdf_links and title and len(title) > 10:
                print(f"📚 Başlık ile DergiPark araması yapılıyor...")
                search_results = self._search_by_title(title)
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
                # Genel 10.32331 pattern (TÜBİTAK dergileri)
                (r'10\.32331/([^.]+)\.(\d+)', r'https://dergipark.org.tr/tr/pub/\1/article/\2'),
                # 10.26466 pattern
                (r'10\.26466/([^.]+)\.(\d+)', r'https://dergipark.org.tr/tr/pub/\1/article/\2'),
                # 10.16953 pattern
                (r'10\.16953/([^.]+)\.(\d+)', r'https://dergipark.org.tr/tr/pub/\1/article/\2'),
                # 10.24014 pattern
                (r'10\.24014/([^.]+)\.(\d+)', r'https://dergipark.org.tr/tr/pub/\1/article/\2'),
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
    
    def _comprehensive_pdf_search(self, soup, base_url):
        """
        Kapsamlı PDF arama stratejileri
        """
        pdf_links = []
        
        # Strateji 1: "Makale Dosyaları" bölümü arama
        pdf_links.extend(self._search_article_files_section(soup, base_url))
        
        # Strateji 2: "Tam Metin" direkt arama
        if not pdf_links:
            pdf_links.extend(self._search_full_text_links(soup, base_url))
        
        # Strateji 3: Download pattern arama
        if not pdf_links:
            pdf_links.extend(self._search_download_patterns(soup, base_url))
        
        # Strateji 4: Right sidebar arama
        if not pdf_links:
            pdf_links.extend(self._search_right_sidebar(soup, base_url))
        
        # Strateji 5: Genel PDF link arama
        if not pdf_links:
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
            
            for section in sections:
                parent = section.find_parent()
                if parent:
                    # Bu section'ın altındaki linkler
                    download_links = self._find_download_links_in_parent(parent)
                    
                    for link_info in download_links:
                        pdf_links.append({
                            'url': link_info['url'],
                            'type': f'section_{section_text.lower().replace(" ", "_")}',
                            'source': 'DergiPark',
                            'quality': 'high',
                            'found_method': f'Section: {section_text}'
                        })
                        print(f"📚 Section PDF bulundu ({section_text}): {link_info['url']}")
                    
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
            
            for sidebar in sidebars:
                download_links = self._find_download_links_in_parent(sidebar)
                
                for link_info in download_links:
                    pdf_links.append({
                        'url': link_info['url'],
                        'type': 'sidebar',
                        'source': 'DergiPark',
                        'quality': 'high',
                        'found_method': f'Sidebar: {selector}'
                    })
                    print(f"📚 Sidebar PDF bulundu: {link_info['url']}")
                
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
                    
                    if len(pdf_links) >= 3:
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
    
    def _search_by_title(self, title):
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
                
                for article_link in article_links[:2]:  # İlk 2 sonuç
                    article_url = 'https://dergipark.org.tr' + article_link['href']
                    print(f"📚 Arama sonucu makale: {article_url}")
                    
                    # Bu makale sayfasından PDF çek
                    search_pdfs = self.find_dergipark_pdfs(article_url, title, {}, None)
                    pdf_links.extend(search_pdfs)
                    
                    if pdf_links:
                        break
        
        except Exception as e:
            print(f"📚 Başlık arama hatası: {e}")
        
        return pdf_links

def find_comprehensive_dergipark_pdfs(url, title, article_data, doi):
    """
    Ana fonksiyon - kapsamlı DergiPark PDF arama
    """
    finder = ComprehensiveDergiParkFinder()
    return finder.find_dergipark_pdfs(url, title, article_data, doi)