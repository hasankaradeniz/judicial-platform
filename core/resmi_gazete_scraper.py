import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
from urllib.parse import urljoin
import logging

logger = logging.getLogger(__name__)

class ResmiGazeteScraper:
    """
    O günkü Resmi Gazete'nin tüm içeriklerini çekmek için scraper sınıfı
    """
    
    def __init__(self):
        self.base_url = "https://www.resmigazete.gov.tr"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def get_daily_content(self, date=None):
        """
        O günkü Resmi Gazete'nin tüm içeriklerini getirir
        """
        if date is None:
            date = datetime.now().date()
        
        try:
            print(f"Bugünün Resmi Gazete içerikleri çekiliyor: {date.strftime('%d.%m.%Y')}")
            
            # Ana sayfadan gerçek içerikleri çek
            real_contents = self._get_daily_gazette_content(date)
            
            if real_contents:
                print(f"✅ Toplam {len(real_contents)} gerçek içerik bulundu!")
                return real_contents
            else:
                print("⚠️ Gerçek içerik bulunamadı, fallback kullanılıyor...")
                return self._get_daily_fallback(date)
            
        except Exception as e:
            print(f"❌ Resmi Gazete scraping hatası: {e}")
            return self._get_daily_fallback(date)
    
    def _try_direct_gazette_access(self, date):
        """
        Doğrudan bugünün sayısına erişmeye çalışır
        """
        try:
            # Bugünün sayı numarasını tahmin et (son 1000 sayı içinde)
            base_number = 32000  # Yaklaşık mevcut sayı
            today_day_of_year = date.timetuple().tm_yday
            estimated_number = base_number + today_day_of_year + 600  # 2025 için tahmin
            
            # Birkaç sayı dene
            for offset in range(-5, 6):  # -5 ile +5 arası dene
                try_number = estimated_number + offset
                
                # Doğrudan sayı URL'sini oluştur
                direct_urls = [
                    f"{self.base_url}/eskiler/{date.strftime('%Y')}/{date.strftime('%m')}/{try_number}.htm",
                    f"{self.base_url}/eskiler/{date.strftime('%Y')}/{date.strftime('%m')}/{try_number}.html",
                    f"{self.base_url}/detay/{try_number}",
                ]
                
                for url in direct_urls:
                    try:
                        print(f"Deneniyor: {url}")
                        response = self.session.get(url, timeout=10)
                        if response.status_code == 200:
                            soup = BeautifulSoup(response.content, 'html.parser')
                            
                            # Bu sayfada bugünün içeriklerini ara
                            content = self._extract_content_from_page(soup, date, url)
                            if content:
                                print(f"Başarılı! Sayı {try_number} bulundu: {len(content)} içerik")
                                return content
                                
                    except:
                        continue
                        
            return []
            
        except Exception as e:
            print(f"Doğrudan erişim hatası: {e}")
            return []
    
    def _extract_content_from_page(self, soup, date, page_url):
        """
        Resmi Gazete sayfasından içerikleri çıkarır
        """
        try:
            content_list = []
            
            # Sayfa başlığını kontrol et
            page_title = soup.find('title')
            if page_title and date.strftime('%d.%m.%Y') not in page_title.get_text():
                return []  # Bu sayfa bugünün değil
            
            # Yürütme ve İdare bölümünü bul
            content_sections = soup.find_all(['div', 'table', 'p'], 
                                           string=re.compile(r'yürütme.*idare|YÜRÜTME.*İDARE', re.I))
            
            if not content_sections:
                # Alternatif yaklaşım: tüm linkleri kontrol et
                all_links = soup.find_all('a', href=True)
                for link in all_links:
                    text = link.get_text(strip=True)
                    href = link.get('href', '')
                    
                    if self._is_valid_gazette_content(text, href):
                        content_info = self._create_content_from_link(text, href, date)
                        if content_info:
                            content_list.append(content_info)
                            
            # Tekrarları kaldır ve döndür
            return self._remove_duplicates(content_list)
            
        except Exception as e:
            print(f"Sayfa içerik çıkarma hatası: {e}")
            return []
    
    def _is_valid_gazette_content(self, text, href):
        """
        Geçerli gazete içeriği mi kontrol eder
        """
        valid_patterns = [
            'yönetmelik', 'atama kararı', 'tebliğ', 'karar',
            'cumhurbaşkanlığı', 'bakanlık', 'üniversite',
            'liste', 'belge', 'genelge'
        ]
        
        text_lower = text.lower()
        return (
            len(text.strip()) > 15 and
            any(pattern in text_lower for pattern in valid_patterns) and
            not any(skip in text_lower for skip in ['footer', 'header', 'menu', 'arşiv'])
        )
    
    def _remove_duplicates(self, content_list):
        """
        Tekrarlanan içerikleri kaldırır
        """
        seen = set()
        unique_content = []
        for item in content_list:
            key = item['baslik'].lower()
            if key not in seen and len(key) > 10:
                seen.add(key)
                unique_content.append(item)
        return unique_content
    
    def _get_daily_gazette_content(self, date):
        """
        Bugünün Resmi Gazete sayısından tüm içerikleri çeker
        """
        try:
            # Ana sayfayı çek
            response = self.session.get(f"{self.base_url}/", timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            print("Ana sayfa yüklendi, günlük içerikler aranıyor...")
            
            # Ana sayfadan bugünün PDF linkini bul
            today_pdf_link = self._extract_today_pdf_link(soup, date)
            
            # Günlük akış içeriklerini çek
            daily_contents = self._extract_daily_flow_contents(soup, date)
            
            all_contents = []
            
            # Ana PDF'i ekle
            if today_pdf_link:
                all_contents.append(today_pdf_link)
                print(f"Ana PDF eklendi: {today_pdf_link['baslik']}")
            
            # Günlük içerikleri ekle
            if daily_contents:
                all_contents.extend(daily_contents)
                print(f"{len(daily_contents)} günlük içerik eklendi")
            
            return all_contents if all_contents else []
            
        except Exception as e:
            print(f"Günlük gazete içerik çekme hatası: {e}")
            return []
    
    def _extract_today_pdf_link(self, soup, date):
        """
        Ana sayfadan bugünün PDF linkini çıkarır
        """
        try:
            # btnPdfGoruntule id'sine sahip linki bul
            pdf_button = soup.find('a', id='btnPdfGoruntule')
            if pdf_button:
                pdf_href = pdf_button.get('href', '')
                if pdf_href and '.pdf' in pdf_href:
                    # Tam URL oluştur
                    if pdf_href.startswith('/'):
                        full_pdf_url = urljoin(self.base_url, pdf_href)
                    else:
                        full_pdf_url = pdf_href
                    
                    # Sayı numarasını çıkar
                    import os
                    pdf_filename = os.path.basename(pdf_href)
                    sayi_match = re.search(r'(\d+)', pdf_filename)
                    sayi = sayi_match.group(1) if sayi_match else date.strftime('%Y%m%d')
                    
                    # Tarih bilgisini span'dan çıkar
                    tarih_span = soup.find('span', id='spanGazeteTarih')
                    if tarih_span:
                        tarih_text = tarih_span.get_text(strip=True)
                        # "13 Temmuz 2025 Tarihli ve 32955 Sayılı Resmî Gazete" formatından bilgi çıkar
                        sayi_match = re.search(r'(\d+)\s+Sayılı', tarih_text)
                        if sayi_match:
                            sayi = sayi_match.group(1)
                    
                    today = date.strftime('%d.%m.%Y')
                    
                    return {
                        'baslik': f'Resmi Gazete - {today} (Sayı: {sayi})',
                        'kategori': 'Günlük Sayı',
                        'sayi': sayi,
                        'tarih': today,
                        'link': full_pdf_url,
                        'ozet': f'{today} tarihli Resmi Gazete günlük sayısı - PDF formatında tüm içerikler',
                        'tur': 'pdf'
                    }
            
            # Alternatif: eskiler klasöründeki PDF linklerini ara
            all_links = soup.find_all('a', href=True)
            for link in all_links:
                href = link.get('href', '')
                if '/eskiler/' in href and '.pdf' in href:
                    # Tarih kontrolü
                    date_pattern = date.strftime('%Y%m%d')
                    if date_pattern in href:
                        full_url = urljoin(self.base_url, href) if href.startswith('/') else href
                        sayi_match = re.search(r'(\d+)', href)
                        sayi = sayi_match.group(1) if sayi_match else date.strftime('%Y%m%d')
                        
                        today = date.strftime('%d.%m.%Y')
                        return {
                            'baslik': f'Resmi Gazete - {today} (Sayı: {sayi})',
                            'kategori': 'Günlük Sayı',
                            'sayi': sayi,
                            'tarih': today,
                            'link': full_url,
                            'ozet': f'{today} tarihli Resmi Gazete günlük sayısı - PDF formatında tüm içerikler',
                            'tur': 'pdf'
                        }
            
            return None
            
        except Exception as e:
            print(f"PDF link çıkarma hatası: {e}")
            return None
    
    def _extract_daily_flow_contents(self, soup, date):
        """
        Günlük akış (gunluk-akis) bölümünden içerikleri çıkarır
        """
        try:
            # gunluk-akis div'ini bul
            daily_flow = soup.find('div', id='gunluk-akis')
            if not daily_flow:
                print("gunluk-akis div'i bulunamadı")
                return []
            
            contents = []
            current_category = None
            
            # HTML içeriği bul
            html_content = daily_flow.find('div', id='html-content')
            if not html_content:
                print("html-content div'i bulunamadı")
                return []
            
            # Tüm elementleri sırayla işle
            for element in html_content.find_all(['div']):
                class_list = element.get('class', [])
                
                # Ana başlık (YÜRÜTME VE İDARE BÖLÜMÜ)
                if 'html-title' in class_list:
                    title_text = element.get_text(strip=True)
                    if 'YÜRÜTME VE İDARE' in title_text:
                        print(f"Yürütme ve İdare bölümü bulundu: {title_text}")
                        current_category = 'yurutme_idare'
                    elif 'İLÂN BÖLÜMÜ' in title_text:
                        # İlan bölümünü atla
                        current_category = 'ilan'
                        break  # İlan bölümünden sonraki içerikleri alma
                
                # Alt başlık (ATAMA KARARI, YÖNETMELİKLER, TEBLİĞLER)
                elif 'html-subtitle' in class_list and current_category == 'yurutme_idare':
                    subtitle_text = element.get_text(strip=True)
                    current_category = subtitle_text.lower()
                    print(f"Alt kategori bulundu: {subtitle_text}")
                
                # İçerik öğesi
                elif 'fihrist-item' in class_list and current_category not in ['ilan', None, 'yurutme_idare']:
                    link_element = element.find('a', href=True)
                    if link_element:
                        href = link_element.get('href', '')
                        text = link_element.get_text(strip=True)
                        
                        # Link kontrolü - daha az kısıtlayıcı
                        if href and href != '#' and '/ilanlar/' not in href and len(text.strip()) > 10:
                            content_item = self._create_daily_content_item(text, href, current_category, date)
                            if content_item:
                                contents.append(content_item)
                                print(f"İçerik eklendi ({current_category}): {text[:50]}...")
            
            print(f"Toplam {len(contents)} günlük içerik bulundu")
            return contents
            
        except Exception as e:
            print(f"Günlük akış çıkarma hatası: {e}")
            return []
    
    def _is_valid_daily_content(self, href, text, category):
        """
        Günlük içeriğin geçerli olup olmadığını kontrol eder
        """
        # Gerçek link kontrolü
        if not href or href == '#':
            return False
        
        # İlan bölümünü atla
        if '/ilanlar/' in href:
            return False
        
        # Minimum metin uzunluğu
        if len(text.strip()) < 10:
            return False
        
        # Kategori bazlı filtreler
        valid_categories = ['atama karari', 'yönetmelikler', 'tebliğler', 'genelgeler']
        
        return any(cat in category for cat in valid_categories)
    
    def _create_daily_content_item(self, title, href, category, date):
        """
        Günlük içerik öğesi oluşturur
        """
        try:
            # URL'yi tam hale getir
            if href.startswith('/'):
                full_url = urljoin(self.base_url, href)
            elif href.startswith('http'):
                full_url = href
            else:
                full_url = f"{self.base_url}/{href}"
            
            # Başlığı temizle (–– işaretlerini kaldır)
            clean_title = title.replace('––', '').strip()
            
            # Kategori belirleme
            category_map = {
                'atama karari': 'Atama Kararı',
                'atama kararı': 'Atama Kararı',
                'yönetmelikler': 'Yönetmelik',
                'tebliğler': 'Tebliğ',
                'genelgeler': 'Genelge'
            }
            
            display_category = category_map.get(category.lower(), 'İdari İşlem')
            
            # Dosya türünü belirle
            file_type = 'pdf' if '.pdf' in href else 'htm'
            
            # Sayı numarasını çıkar
            sayi_match = re.search(r'(\d{8}-\d+)', href)
            sayi = sayi_match.group(1) if sayi_match else date.strftime('%Y%m%d')
            
            return {
                'baslik': clean_title,
                'kategori': display_category,
                'sayi': sayi,
                'tarih': date.strftime('%d.%m.%Y'),
                'link': full_url,
                'ozet': f"{display_category}: {clean_title[:60]}..." if len(clean_title) > 60 else f"{display_category}: {clean_title}",
                'tur': file_type
            }
            
        except Exception as e:
            print(f"Günlük içerik öğesi oluşturma hatası: {e}")
            return None
    
    def _find_today_pdf(self, soup, date):
        """
        Ana sayfadan bugünün PDF linkini bulur
        """
        today_patterns = [
            date.strftime('%Y%m%d'),
            date.strftime('%d.%m.%Y'),
            date.strftime('%d/%m/%Y'),
            date.strftime('%d-%m-%Y')
        ]
        
        # Tüm PDF linklerini kontrol et
        pdf_links = soup.find_all('a', href=re.compile(r'\.pdf'))
        
        for link in pdf_links:
            href = link.get('href', '')
            text = link.get_text(strip=True)
            
            # Bugünün tarihini içeren PDF'i bul
            for pattern in today_patterns:
                if pattern in href or pattern in text:
                    full_url = urljoin(self.base_url, href) if href.startswith('/') else href
                    print(f"Bugünün PDF'i bulundu: {text}")
                    return full_url
        
        # Alternatif: "günlük" veya "son sayı" linklerini kontrol et
        daily_links = soup.find_all('a', href=re.compile(r'/(gunluk|son|today)'))
        for link in daily_links:
            href = link.get('href', '')
            full_url = urljoin(self.base_url, href) if href.startswith('/') else href
            print(f"Günlük sayı linki bulundu: {link.get_text(strip=True)}")
            return full_url
        
        return None
    
    def _is_unwanted_link(self, href, text):
        """
        İstenmeyen linkleri filtreler (footer, header, arşiv vb.)
        """
        unwanted_patterns = [
            'footer', 'header', 'menu', 'sosyal', 'facebook', 'twitter', 'instagram',
            'linkedin', 'hakkımızda', 'iletişim', 'gizlilik', 'kullanım', 'şartları',
            'arşiv', 'eski', 'geçmiş', 'mükerrer', 'ilan', 'duyuru', 'haberler',
            'sitemap', 'rss', 'xml', 'arama', 'search', 'login', 'kayıt',
            '#', 'javascript:', 'mailto:', 'tel:', 'ftp:', 'file:'
        ]
        
        href_lower = href.lower()
        text_lower = text.lower()
        
        # Boş veya çok kısa linkler
        if not href or not text or len(text.strip()) < 5:
            return True
            
        # İstenmeyen kalıpları kontrol et
        for pattern in unwanted_patterns:
            if pattern in href_lower or pattern in text_lower:
                return True
                
        return False
    
    def _is_todays_content(self, href, text, date):
        """
        Günün içeriği olup olmadığını kontrol eder
        """
        # Geçerli içerik anahtar kelimeleri
        valid_keywords = [
            'yönetmelik', 'atama', 'karar', 'tebliğ', 'genelge',
            'cumhurbaşkanlığı', 'bakanlık', 'müdürlük', 'başkanlık', 
            'üniversite', 'kurul', 'komisyon', 'liste', 'belge',
            'daire', 'genel', 'merkez', 'bölge', 'il', 'pdf'
        ]
        
        text_lower = text.lower()
        href_lower = href.lower()
        
        # Bugünün tarih formatlarını kontrol et
        today_patterns = [
            date.strftime('%Y%m%d'),
            date.strftime('%d.%m.%Y'),
            date.strftime('%d/%m/%Y'),
            date.strftime('%d-%m-%Y'),
            '2025', 'temmuz', 'july'
        ]
        
        # Tarih kontrolü
        has_date = any(pattern in href_lower or pattern in text_lower for pattern in today_patterns)
        
        # En az bir geçerli anahtar kelime içermeli VEYA PDF linki olmalı
        has_keyword = any(keyword in text_lower for keyword in valid_keywords)
        
        # Minimum uzunluk kontrolü
        min_length = len(text.strip()) >= 10
        
        # PDF veya detay sayfası linki
        is_content_link = (
            '.pdf' in href_lower or 
            'detay' in href_lower or 
            '/eskiler/' in href_lower or
            'sayı' in text_lower or
            'pdf' in text_lower
        )
        
        # Günün PDF'i mi?
        is_todays_pdf = has_date and ('.pdf' in href_lower or 'pdf' in text_lower)
        
        return min_length and (
            (has_keyword and is_content_link) or 
            is_todays_pdf or 
            (has_date and len(text) > 20)
        )
    
    def _create_content_from_link(self, title, href, date):
        """
        Link'ten içerik öğesi oluşturur
        """
        try:
            # URL'yi tam hale getir
            if href.startswith('/'):
                full_url = urljoin(self.base_url, href)
            elif href.startswith('http'):
                full_url = href
            else:
                full_url = f"{self.base_url}/{href}"
            
            # Kategori ve tür belirle
            category_info = self._determine_category_from_title(title)
            
            return {
                'baslik': title[:150],
                'kategori': category_info['kategori'],
                'sayi': self._extract_number_from_title(title),
                'tarih': date.strftime('%d.%m.%Y'),
                'link': full_url,
                'ozet': f"{category_info['kategori']}: {title[:80]}..." if len(title) > 80 else f"{category_info['kategori']}: {title}",
                'tur': category_info['tur']
            }
            
        except Exception as e:
            print(f"Link içerik oluşturma hatası: {e}")
            return None
    
    def _get_gazette_detail_content(self, pdf_url, date):
        """
        Resmi Gazete detay sayfasından içerikleri çeker
        """
        try:
            # PDF URL'den detay sayfa URL'sini oluştur
            detail_url = pdf_url.replace('.pdf', '').replace('/eskiler/', '/detay/')
            
            response = self.session.get(detail_url, timeout=15)
            if response.status_code != 200:
                # Doğrudan PDF sayfasını dene
                response = self.session.get(pdf_url, timeout=15)
                if response.status_code != 200:
                    return []
            
            soup = BeautifulSoup(response.content, 'html.parser')
            content_list = []
            
            # Yürütme ve İdare bölümünü bul
            yurutme_sections = [
                'yürütme ve idare',
                'yurutme ve idare', 
                'yürütme',
                'idare',
                'atama kararı',
                'yönetmelik',
                'tebliğ'
            ]
            
            # Tüm linkleri ve metinleri kontrol et
            all_links = soup.find_all('a', href=True)
            all_headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'strong', 'b'])
            all_texts = soup.find_all(['p', 'div', 'li', 'td'])
            
            # Başlıklardan içerikleri çıkar
            for heading in all_headings:
                text = heading.get_text(strip=True)
                if any(section in text.lower() for section in yurutme_sections):
                    self._extract_content_from_section(heading, content_list, date)
            
            # Linklerden içerikleri çıkar
            for link in all_links:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                if self._is_valid_content(text, href):
                    content_info = self._create_content_item(text, href, date)
                    if content_info:
                        content_list.append(content_info)
            
            # Metin içeriklerinden çıkar
            for text_elem in all_texts:
                text = text_elem.get_text(strip=True)
                if self._is_valid_content_text(text):
                    content_info = self._create_content_from_text(text, date, text_elem)
                    if content_info:
                        content_list.append(content_info)
            
            # Tekrarları kaldır
            seen = set()
            unique_content = []
            for item in content_list:
                key = item['baslik'].lower()
                if key not in seen:
                    seen.add(key)
                    unique_content.append(item)
            
            print(f"Toplam {len(unique_content)} benzersiz içerik bulundu")
            return unique_content[:20]  # İlk 20'yi döndür
            
        except Exception as e:
            print(f"Detay içerik çekme hatası: {e}")
            return []
    
    def _extract_content_from_section(self, heading, content_list, date):
        """
        Bir başlık bölümünden içerikleri çıkarır
        """
        try:
            # Başlığın altındaki içerikleri bul
            next_elements = heading.find_next_siblings()
            
            for elem in next_elements[:10]:  # İlk 10 elementi kontrol et
                if elem.name in ['ul', 'ol', 'div', 'p']:
                    links = elem.find_all('a', href=True)
                    for link in links:
                        text = link.get_text(strip=True)
                        href = link.get('href', '')
                        
                        if self._is_valid_content(text, href):
                            content_info = self._create_content_item(text, href, date)
                            if content_info:
                                content_list.append(content_info)
                
                # Bir sonraki ana başlığa geldiysek dur
                if elem.name in ['h1', 'h2', 'h3'] and elem != heading:
                    break
                    
        except Exception as e:
            print(f"Bölüm içerik çıkarma hatası: {e}")
    
    def _is_valid_content(self, text, href):
        """
        İçeriğin geçerli olup olmadığını kontrol eder
        """
        if not text or len(text) < 10:
            return False
        
        # Geçerli içerik anahtar kelimeleri
        valid_keywords = [
            'yönetmelik', 'atama', 'karar', 'tebliğ', 'genelge',
            'bakanlık', 'müdürlük', 'başkanlık', 'kurul',
            'hakkında', 'dair', 'değişiklik', 'ek'
        ]
        
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in valid_keywords)
    
    def _is_valid_content_text(self, text):
        """
        Metin içeriğinin geçerli olup olmadığını kontrol eder
        """
        if not text or len(text) < 20:
            return False
        
        # Yürütme ve İdare içerikleri
        valid_patterns = [
            'atama kararı',
            'yönetmelik',
            'tebliğ',
            'genelge',
            'cumhurbaşkanlığı kararı',
            'bakanlar kurulu kararı'
        ]
        
        text_lower = text.lower()
        return any(pattern in text_lower for pattern in valid_patterns)
    
    def _create_content_item(self, title, href, date):
        """
        İçerik öğesi oluşturur
        """
        try:
            # URL'yi tam hale getir
            if href.startswith('/'):
                full_url = urljoin(self.base_url, href)
            elif href.startswith('http'):
                full_url = href
            else:
                full_url = f"{self.base_url}/{href}"
            
            # Kategori ve tür belirle
            category_info = self._determine_category_from_title(title)
            
            return {
                'baslik': title[:150],
                'kategori': category_info['kategori'],
                'sayi': self._extract_number_from_title(title),
                'tarih': date.strftime('%d.%m.%Y'),
                'link': full_url,
                'ozet': f"{category_info['kategori']}: {title[:80]}..." if len(title) > 80 else f"{category_info['kategori']}: {title}",
                'tur': category_info['tur']
            }
            
        except Exception as e:
            print(f"İçerik öğesi oluşturma hatası: {e}")
            return None
    
    def _create_content_from_text(self, text, date, parent_element=None):
        """
        Metin içeriğinden içerik öğesi oluşturur
        """
        try:
            # Başlığı çıkar (ilk 100 karakter)
            title = text[:100].strip()
            
            category_info = self._determine_category_from_title(text)
            
            # Parent element içinde link arama
            content_link = self._find_content_link(title, parent_element, date)
            
            return {
                'baslik': title,
                'kategori': category_info['kategori'],
                'sayi': self._extract_number_from_title(text),
                'tarih': date.strftime('%d.%m.%Y'),
                'link': content_link,
                'ozet': f"{category_info['kategori']}: {title[:60]}..." if len(title) > 60 else f"{category_info['kategori']}: {title}",
                'tur': category_info['tur']
            }
            
        except Exception as e:
            print(f"Metin içerik oluşturma hatası: {e}")
            return None
    
    def _determine_category_from_title(self, title):
        """
        Başlıktan kategori ve tür belirler
        """
        title_lower = title.lower()
        
        if 'atama kararı' in title_lower or 'atama' in title_lower:
            return {'kategori': 'Atama Kararı', 'tur': 'atama'}
        elif 'yönetmelik' in title_lower:
            return {'kategori': 'Yönetmelik', 'tur': 'yönetmelik'}
        elif 'tebliğ' in title_lower:
            return {'kategori': 'Tebliğ', 'tur': 'tebliğ'}
        elif 'karar' in title_lower:
            return {'kategori': 'Karar', 'tur': 'karar'}
        elif 'genelge' in title_lower:
            return {'kategori': 'Genelge', 'tur': 'genelge'}
        else:
            return {'kategori': 'İdari İşlem', 'tur': 'idari'}
    
    def _extract_number_from_title(self, title):
        """
        Başlıktan sayı çıkarır
        """
        match = re.search(r'(\d{4,})', title)
        if match:
            return match.group(1)
        return datetime.now().strftime('%Y%m%d')[-5:]
    
    def _find_content_link(self, title, parent_element, date):
        """
        İçerik için gerçek link bulur
        """
        try:
            if not parent_element:
                return self._generate_search_link(title)
            
            # Parent element içinde link arama
            link = parent_element.find('a', href=True)
            if link:
                href = link.get('href', '')
                if href and href != '#':
                    full_url = urljoin(self.base_url, href) if href.startswith('/') else href
                    print(f"İçerik linki bulundu: {title[:50]}... -> {full_url}")
                    return full_url
            
            # Parent'ın parent'ında arama
            if parent_element.parent:
                link = parent_element.parent.find('a', href=True)
                if link:
                    href = link.get('href', '')
                    if href and href != '#':
                        full_url = urljoin(self.base_url, href) if href.startswith('/') else href
                        print(f"Üst seviye link bulundu: {title[:50]}... -> {full_url}")
                        return full_url
            
            # Başlık bazlı arama linki
            return self._generate_search_link(title)
            
        except Exception as e:
            print(f"Link bulma hatası: {e}")
            return self._generate_search_link(title)
    
    def _generate_search_link(self, title):
        """
        İçerik başlığı için arama linki oluşturur
        """
        try:
            # Başlıktan anahtar kelimeleri çıkar
            keywords = []
            
            if 'yönetmelik' in title.lower():
                keywords.append('yönetmelik')
            if 'atama' in title.lower():
                keywords.append('atama')
            if 'tebliğ' in title.lower():
                keywords.append('tebliğ')
            if 'karar' in title.lower():
                keywords.append('karar')
            
            # Üniversite/kurum adlarını çıkar
            words = title.split()
            for word in words:
                if len(word) > 5 and any(term in word.lower() for term in ['üniversitesi', 'bakanlığı', 'müdürlüğü']):
                    keywords.append(word)
            
            # Arama parametresi oluştur
            search_query = ' '.join(keywords[:3])  # İlk 3 anahtar kelime
            
            if search_query.strip():
                import urllib.parse
                encoded_query = urllib.parse.quote(search_query)
                search_url = f"https://www.resmigazete.gov.tr/arama?q={encoded_query}"
                print(f"Arama linki oluşturuldu: {title[:50]}... -> {search_url}")
                return search_url
            else:
                return 'https://www.resmigazete.gov.tr/'
                
        except Exception as e:
            print(f"Arama linki oluşturma hatası: {e}")
            return 'https://www.resmigazete.gov.tr/'
    
    def _get_daily_fallback(self, date):
        """
        Sadece günlük sayı - fallback
        """
        today = date.strftime('%d.%m.%Y')
        
        # Bugünün muhtemel sayı numarasını hesapla
        base_date = datetime(2025, 1, 1).date()
        days_passed = (date - base_date).days
        estimated_number = 32600 + days_passed
        
        return [
            {
                'baslik': f'Resmi Gazete - {today} (Sayı: {estimated_number})',
                'kategori': 'Günlük Sayı',
                'sayi': str(estimated_number),
                'tarih': today,
                'link': 'https://www.resmigazete.gov.tr/',
                'ozet': f'{today} tarihli Resmi Gazete günlük sayısı - Tüm resmi yayınları içerir',
                'tur': 'resmigazete'
            }
        ]

def get_resmi_gazete_content():
    """
    Views'da kullanılmak üzere basit fonksiyon
    """
    scraper = ResmiGazeteScraper()
    return scraper.get_daily_content()