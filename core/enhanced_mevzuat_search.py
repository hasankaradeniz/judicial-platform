import requests
from bs4 import BeautifulSoup
import logging
from urllib.parse import urljoin, quote, parse_qs, urlparse
from django.core.cache import cache
from django.http import JsonResponse
import re
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class EnhancedMevzuatSearcher:
    """mevzuat-mcp'den ilham alınarak geliştirilmiş mevzuat arama sistemi"""
    
    def __init__(self):
        self.base_url = "https://www.mevzuat.gov.tr"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'tr-TR,tr;q=0.9',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # Mevzuat türleri - mcp'den alınan mapping
        self.mevzuat_types = {
            'kanun': 1,
            'khk': 4,
            'tuzuk': 2,
            'cumhurbaskanligi_kararnamesi': 19,
            'yonetmelik': 7,
            'teblig': 9,
            'genelge': 12,
            'all': 0
        }
    
    def search_legislation(self, query, mevzuat_type=None, page=1, per_page=20):
        """Gelişmiş mevzuat arama - mcp mantığıyla"""
        try:
            logger.info(f"Enhanced search: {query}, type: {mevzuat_type}, page: {page}")
            
            # Cache key oluştur
            cache_key = self._generate_cache_key(query, mevzuat_type, page)
            cached = cache.get(cache_key)
            if cached:
                logger.info("Returning from cache")
                return cached
            
            # Arama tipini belirle
            search_type = self._determine_search_type(query)
            
            # Uygun arama metodunu çağır
            if search_type == 'number':
                results = self._search_by_number(query)
            elif search_type == 'date':
                results = self._search_by_date(query)
            else:
                results = self._search_by_text(query, mevzuat_type, page)
            
            # Sonuçları zenginleştir
            results = self._enrich_results(results)
            
            # Cache'le
            if results['total_count'] > 0:
                cache.set(cache_key, results, 3600)  # 1 saat
            
            return results
            
        except Exception as e:
            logger.error(f"Search error: {str(e)}")
            return self._error_response(str(e), page, per_page)
    
    def _determine_search_type(self, query):
        """Arama tipini belirle - sayı mı, tarih mi, metin mi?"""
        # Sadece sayı mı? (örn: 6102)
        if re.match(r'^\d+$', query.strip()):
            return 'number'
        
        # Tarih formatı mı? (örn: 01.01.2020 veya 2020)
        if re.match(r'^\d{2}\.\d{2}\.\d{4}$', query.strip()) or re.match(r'^\d{4}$', query.strip()):
            return 'date'
        
        return 'text'
    
    def _search_by_number(self, number):
        """Mevzuat numarasına göre ara"""
        logger.info(f"Searching by number: {number}")
        
        # Direkt mevzuat sayfasını dene
        url = f"{self.base_url}/mevzuat?MevzuatNo={number}"
        
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Mevzuat bulunduysa
                title_elem = soup.find('h3', class_='baslik') or soup.find('h1')
                if title_elem:
                    result = self._parse_detail_page(soup, number)
                    if result:
                        return {
                            'results': [result],
                            'total_count': 1,
                            'page': 1,
                            'per_page': 20,
                            'has_next': False,
                            'has_previous': False,
                            'source': 'mevzuat.gov.tr',
                            'search_type': 'number'
                        }
        except Exception as e:
            logger.error(f"Number search error: {str(e)}")
        
        # Bulunamazsa normal arama yap
        return self._search_by_text(number, None, 1)
    
    def _search_by_date(self, date_query):
        """Tarihe göre ara"""
        logger.info(f"Searching by date: {date_query}")
        
        # Tarih formatını düzenle
        search_params = {
            'q': '',
            'tarih': date_query
        }
        
        return self._perform_search(search_params, 1, 20)
    
    def _search_by_text(self, query, mevzuat_type=None, page=1):
        """Metne göre ara - ana arama fonksiyonu"""
        logger.info(f"Text search: {query}")
        
        # Form verisi hazırla
        form_data = {
            'AranacakMetin': query
        }
        
        # Mevzuat türü varsa ekle
        if mevzuat_type and mevzuat_type in self.mevzuat_types:
            form_data['MevzuatTur'] = self.mevzuat_types[mevzuat_type]
        
        return self._perform_search(form_data, page, 20)
    
    def _perform_search(self, search_params, page, per_page):
        """Gerçek arama işlemi"""
        try:
            # Token al
            token = self._get_antiforgery_token()
            if token:
                search_params['antiforgerytoken'] = token
            
            # Arama yap
            search_url = f"{self.base_url}/aramasonuc"
            response = self.session.post(search_url, data=search_params, timeout=15)
            
            if response.status_code != 200:
                logger.error(f"Search returned {response.status_code}")
                return self._empty_result(page, per_page)
            
            # Sonuçları parse et
            soup = BeautifulSoup(response.text, 'html.parser')
            results = self._parse_search_results(soup)
            
            # Sayfalama
            total_count = len(results)
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            paginated_results = results[start_idx:end_idx]
            
            return {
                'results': paginated_results,
                'total_count': total_count,
                'page': page,
                'per_page': per_page,
                'has_next': end_idx < total_count,
                'has_previous': page > 1,
                'source': 'mevzuat.gov.tr',
                'search_params': search_params
            }
            
        except Exception as e:
            logger.error(f"Search error: {str(e)}")
            return self._empty_result(page, per_page)
    
    def _parse_search_results(self, soup):
        """Arama sonuçlarını parse et - mcp mantığıyla"""
        results = []
        
        # Önce DataTable'ı bul
        tables = soup.find_all('table', id=re.compile(r'.*Datatable.*', re.I))
        
        for table in tables:
            tbody = table.find('tbody')
            if not tbody:
                continue
            
            for row in tbody.find_all('tr'):
                result = self._parse_result_row(row)
                if result:
                    results.append(result)
        
        # Eğer tablo yoksa alternatif yapıları dene
        if not results:
            # Div bazlı sonuçlar
            result_divs = soup.find_all('div', class_=re.compile(r'result|sonuc', re.I))
            for div in result_divs:
                result = self._parse_result_div(div)
                if result:
                    results.append(result)
        
        return results
    
    def _parse_result_row(self, row):
        """Tablo satırını parse et"""
        try:
            cells = row.find_all('td')
            if len(cells) < 2:
                return None
            
            # Mevzuat No
            no_cell = cells[0]
            no_link = no_cell.find('a')
            if not no_link:
                return None
            
            mevzuat_no = no_link.get_text(strip=True)
            href = no_link.get('href', '')
            
            # Başlık ve detaylar
            title_cell = cells[1]
            title_link = title_cell.find('a')
            if not title_link:
                return None
            
            # Başlığı temizle
            title_div = title_link.find('div')
            title = self._clean_html(title_div.get_text(strip=True) if title_div else title_link.get_text(strip=True))
            
            # Detayları al
            details_div = title_cell.find('div', class_='mt-1')
            details = self._extract_details(details_div) if details_div else {}
            
            # URL parametrelerini parse et
            url_params = self._extract_url_params(href)
            
            # Sonuç oluştur
            result = {
                'mevzuat_no': mevzuat_no,
                'title': title,
                'url': urljoin(self.base_url, href),
                'mevzuat_type': details.get('type', 'Belirtilmemiş'),
                'date': details.get('date', ''),
                'rg_date': details.get('rg_date', ''),
                'rg_no': details.get('rg_no', ''),
                'tertip': url_params.get('MevzuatTertip', ''),
                'summary': title[:200] + '...' if len(title) > 200 else title,
                'metadata': details
            }
            
            # PDF URL'lerini oluştur
            result.update(self._generate_pdf_urls(url_params, details.get('type', '')))
            
            return result
            
        except Exception as e:
            logger.error(f"Row parse error: {str(e)}")
            return None
    
    def _parse_result_div(self, div):
        """Div bazlı sonucu parse et"""
        try:
            link = div.find('a', href=True)
            if not link:
                return None
            
            title = self._clean_html(link.get_text(strip=True))
            href = link['href']
            
            # Basit sonuç
            result = {
                'title': title,
                'url': urljoin(self.base_url, href),
                'mevzuat_type': self._guess_type_from_title(title),
                'summary': title
            }
            
            # URL'den bilgi çıkar
            url_params = self._extract_url_params(href)
            if url_params.get('MevzuatNo'):
                result['mevzuat_no'] = url_params['MevzuatNo']
                result.update(self._generate_pdf_urls(url_params, result['mevzuat_type']))
            
            return result
            
        except Exception as e:
            logger.error(f"Div parse error: {str(e)}")
            return None
    
    def _parse_detail_page(self, soup, mevzuat_no):
        """Detay sayfasını parse et"""
        try:
            result = {'mevzuat_no': mevzuat_no}
            
            # Başlık
            title_elem = soup.find('h3', class_='baslik') or soup.find('h1')
            if title_elem:
                result['title'] = self._clean_html(title_elem.get_text(strip=True))
            
            # Bilgi tablosu
            info_table = soup.find('table', class_='mevzuat-bilgi-table')
            if info_table:
                for row in info_table.find_all('tr'):
                    cells = row.find_all('td')
                    if len(cells) == 2:
                        key = cells[0].get_text(strip=True).lower()
                        value = cells[1].get_text(strip=True)
                        
                        if 'tür' in key:
                            result['mevzuat_type'] = value
                        elif 'tarih' in key and 'resm' in key:
                            result['rg_date'] = value
                        elif 'sayı' in key:
                            result['rg_no'] = value
                        elif 'tertip' in key:
                            result['tertip'] = value
            
            # URL
            result['url'] = f"{self.base_url}/mevzuat?MevzuatNo={mevzuat_no}"
            
            # PDF URL'leri
            result.update(self._generate_pdf_urls({'MevzuatNo': mevzuat_no}, result.get('mevzuat_type', '')))
            
            return result
            
        except Exception as e:
            logger.error(f"Detail parse error: {str(e)}")
            return None
    
    def _extract_details(self, details_div):
        """Detay div'inden bilgileri çıkar"""
        details = {}
        
        try:
            text = details_div.get_text()
            html = str(details_div)
            
            # Tür
            type_match = re.search(r'<i>([^<]+)</i>', html)
            if type_match:
                details['type'] = type_match.group(1).strip()
            
            # Tarihler
            rg_date_match = re.search(r'Resmî Gazete Tarihi:\s*</b></i>\s*([\d.]+)', text)
            if rg_date_match:
                details['rg_date'] = rg_date_match.group(1)
            
            kabul_date_match = re.search(r'Kabul Tarihi:\s*</b></i>\s*([\d.]+)', text)
            if kabul_date_match:
                details['date'] = kabul_date_match.group(1)
            
            # RG Sayısı
            rg_no_match = re.search(r'Sayısı:\s*</b></i>\s*(\d+)', text)
            if rg_no_match:
                details['rg_no'] = rg_no_match.group(1)
            
            # Tertip
            tertip_match = re.search(r'Tertip:\s*</b></i>\s*(\d+)', text)
            if tertip_match:
                details['tertip'] = tertip_match.group(1)
            
        except Exception as e:
            logger.error(f"Detail extraction error: {str(e)}")
        
        return details
    
    def _generate_pdf_urls(self, url_params, mevzuat_type_text):
        """PDF URL'lerini oluştur - çoklu format desteği"""
        pdf_urls = {}
        
        mevzuat_no = url_params.get('MevzuatNo')
        if not mevzuat_no:
            return pdf_urls
        
        # Format 1: Direkt PDF
        tur = url_params.get('MevzuatTur', '1')
        tertip = url_params.get('MevzuatTertip', '5')
        pdf_urls['direct_pdf'] = f"{self.base_url}/MevzuatMetin/{tur}.{tertip}.{mevzuat_no}.pdf"
        
        # Format 2: Generate endpoint
        type_text = self._normalize_type_for_url(mevzuat_type_text)
        pdf_urls['generate_pdf'] = f"{self.base_url}/File/GeneratePdf?mevzuatNo={mevzuat_no}&mevzuatTur={type_text}&mevzuatTertip={tertip}"
        
        # Format 3: API endpoint
        pdf_urls['api_pdf'] = f"{self.base_url}/api/pdf/{mevzuat_no}"
        
        # Ana PDF URL
        pdf_urls['pdf_url'] = pdf_urls['direct_pdf']
        
        return pdf_urls
    
    def _extract_url_params(self, url):
        """URL'den parametreleri çıkar"""
        params = {}
        
        # Query string parse
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        
        for key, value in query_params.items():
            params[key] = value[0] if value else ''
        
        # Regex ile de dene
        patterns = {
            'MevzuatNo': r'MevzuatNo=(\d+)',
            'MevzuatTur': r'MevzuatTur=(\d+)',
            'MevzuatTertip': r'MevzuatTertip=(\d+)'
        }
        
        for key, pattern in patterns.items():
            if key not in params:
                match = re.search(pattern, url)
                if match:
                    params[key] = match.group(1)
        
        return params
    
    def _enrich_results(self, results_data):
        """Sonuçları zenginleştir"""
        if 'results' in results_data:
            for result in results_data['results']:
                # Mevzuat türüne göre ikon ekle
                result['icon'] = self._get_type_icon(result.get('mevzuat_type', ''))
                
                # Tarih formatla
                if result.get('date'):
                    result['formatted_date'] = self._format_date(result['date'])
                
                # Arama terimi highlight
                if 'search_params' in results_data:
                    query = results_data['search_params'].get('AranacakMetin', '')
                    if query:
                        result['highlighted_title'] = self._highlight_text(result['title'], query)
        
        return results_data
    
    def _get_type_icon(self, mevzuat_type):
        """Mevzuat türüne göre ikon döndür"""
        icons = {
            'Kanun': '⚖️',
            'Yönetmelik': '📋',
            'Tebliğ': '📢',
            'Karar': '🔨',
            'Genelge': '📨',
            'Tüzük': '📜'
        }
        return icons.get(mevzuat_type, '📄')
    
    def _format_date(self, date_str):
        """Tarihi formatla"""
        try:
            if '.' in date_str:
                parts = date_str.split('.')
                if len(parts) == 3:
                    return f"{parts[0]} {self._get_month_name(int(parts[1]))} {parts[2]}"
        except:
            pass
        return date_str
    
    def _get_month_name(self, month):
        """Ay adını döndür"""
        months = ['', 'Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran',
                  'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık']
        return months[month] if 0 < month < 13 else str(month)
    
    def _highlight_text(self, text, query):
        """Arama terimini vurgula"""
        for term in query.split():
            if len(term) > 2:
                pattern = re.compile(re.escape(term), re.IGNORECASE)
                text = pattern.sub(f'<mark>{term}</mark>', text)
        return text
    
    def _normalize_type_for_url(self, type_text):
        """Tür metnini URL için normalize et"""
        type_map = {
            'kanun': 'Kanun',
            'tebliğ': 'Teblig',
            'yönetmelik': 'Yonetmelik',
            'karar': 'Karar',
            'genelge': 'Genelge',
            'tüzük': 'Tuzuk'
        }
        
        type_lower = type_text.lower()
        for key, value in type_map.items():
            if key in type_lower:
                return value
        
        return 'Kanun'
    
    def _clean_html(self, text):
        """HTML etiketlerini temizle"""
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def _guess_type_from_title(self, title):
        """Başlıktan tür tahmin et"""
        title_lower = title.lower()
        if 'kanun' in title_lower:
            return 'Kanun'
        elif 'yönetmelik' in title_lower:
            return 'Yönetmelik'
        elif 'tebliğ' in title_lower:
            return 'Tebliğ'
        elif 'karar' in title_lower:
            return 'Karar'
        elif 'genelge' in title_lower:
            return 'Genelge'
        elif 'tüzük' in title_lower:
            return 'Tüzük'
        return 'Diğer'
    
    def _generate_cache_key(self, query, mevzuat_type, page):
        """Cache key oluştur"""
        key_parts = [
            'mevzuat_search',
            query.lower().replace(' ', '_'),
            mevzuat_type or 'all',
            str(page)
        ]
        return '_'.join(key_parts)
    
    def _get_antiforgery_token(self):
        """Ana sayfadan token al"""
        try:
            response = self.session.get(self.base_url, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            token_input = soup.find('input', {'name': 'antiforgerytoken'})
            if token_input:
                return token_input.get('value', '')
            
            return ''
        except Exception as e:
            logger.error(f"Token error: {str(e)}")
            return ''
    
    def _empty_result(self, page, per_page):
        """Boş sonuç"""
        return {
            'results': [],
            'total_count': 0,
            'page': page,
            'per_page': per_page,
            'has_next': False,
            'has_previous': False,
            'source': 'mevzuat.gov.tr'
        }
    
    def _error_response(self, error, page, per_page):
        """Hata sonucu"""
        result = self._empty_result(page, per_page)
        result['error'] = error
        return result
    
    # API için ek metodlar
    def get_mevzuat_detail(self, mevzuat_no):
        """Mevzuat detayını getir"""
        cache_key = f"mevzuat_detail_{mevzuat_no}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        url = f"{self.base_url}/mevzuat?MevzuatNo={mevzuat_no}"
        
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                detail = self._parse_detail_page(soup, mevzuat_no)
                
                if detail:
                    # İçeriği de al
                    content_div = soup.find('div', id='mevzuat-content') or soup.find('div', class_='mevzuat-icerik')
                    if content_div:
                        detail['content'] = content_div.get_text(strip=True)
                    
                    cache.set(cache_key, detail, 7200)  # 2 saat
                    return detail
        
        except Exception as e:
            logger.error(f"Detail fetch error: {str(e)}")
        
        return None
    
    def get_mevzuat_pdf(self, mevzuat_no, pdf_type='direct'):
        """PDF içeriğini getir"""
        pdf_urls = self._generate_pdf_urls({'MevzuatNo': mevzuat_no}, '')
        pdf_url = pdf_urls.get(f'{pdf_type}_pdf', pdf_urls.get('pdf_url'))
        
        if not pdf_url:
            return None
        
        try:
            response = self.session.get(pdf_url, timeout=30, stream=True)
            if response.status_code == 200:
                return response.content
        except Exception as e:
            logger.error(f"PDF fetch error: {str(e)}")
        
        return None