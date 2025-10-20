import requests
from bs4 import BeautifulSoup
import logging
from urllib.parse import urljoin, quote
from django.core.cache import cache
import re

logger = logging.getLogger(__name__)

class SimpleMevzuatSearcher:
    """Mevzuat.gov.tr için güncellenmiş arama - çoklu PDF format desteği"""
    
    def __init__(self):
        self.base_url = "https://www.mevzuat.gov.tr"
        self.search_url = "https://www.mevzuat.gov.tr/aramasonuc"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'tr-TR,tr;q=0.9',
            'Referer': 'https://www.mevzuat.gov.tr/',
            'Origin': 'https://www.mevzuat.gov.tr'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def search_legislation(self, query, mevzuat_type=None, page=1, per_page=20):
        """Mevzuat.gov.tr'den arama yap"""
        try:
            logger.info(f"Mevzuat arama: {query}")
            
            # Cache kontrolü
            cache_key = f"mevzuat_search_{query}_{mevzuat_type}_{page}".replace(' ', '_')
            cached = cache.get(cache_key)
            if cached:
                logger.info("Cache'den döndürülüyor")
                return cached
            
            # 1. Ana sayfadan antiforgery token al
            antiforgery_token = self._get_antiforgery_token()
            
            # 2. Arama form'unu gönder
            form_data = {
                'AranacakMetin': query
            }
            
            # Token varsa ekle
            if antiforgery_token:
                form_data['antiforgerytoken'] = antiforgery_token
            
            logger.info(f"POST arama: {self.search_url}")
            response = self.session.post(self.search_url, data=form_data, timeout=15)
            
            if response.status_code != 200:
                logger.error(f"HTTP {response.status_code} hatası")
                return self._empty_result(page, per_page)
            
            # 3. HTML'i parse et
            results = self._parse_search_results(response.text, query)
            
            # 4. Sonuçları döndür
            total_count = len(results)
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            paginated_results = results[start_idx:end_idx]
            
            result_data = {
                'results': paginated_results,
                'total_count': total_count,
                'page': page,
                'per_page': per_page,
                'has_next': end_idx < total_count,
                'has_previous': page > 1,
                'source': 'mevzuat.gov.tr'
            }
            
            # Cache'e kaydet
            if results:
                cache.set(cache_key, result_data, 1800)  # 30 dakika
            
            logger.info(f"Arama tamamlandı: {len(results)} sonuç")
            return result_data
            
        except Exception as e:
            logger.error(f"Arama hatası: {str(e)}")
            return self._empty_result(page, per_page, error=str(e))
    
    def _get_antiforgery_token(self):
        """Ana sayfadan antiforgery token al"""
        try:
            response = self.session.get(self.base_url, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # antiforgerytoken input'unu bul
            token_input = soup.find('input', {'name': 'antiforgerytoken'})
            if token_input:
                token_value = token_input.get('value', '')
                logger.info("Antiforgery token alındı")
                return token_value
            
            logger.warning("Antiforgery token bulunamadı")
            return ''
            
        except Exception as e:
            logger.error(f"Token alma hatası: {str(e)}")
            return ''
    
    def _parse_search_results(self, html_content, query):
        """Arama sonuçlarını parse et"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            results = []
            
            # Başlık tablosunu bul
            baslik_table = soup.find('table', id='Baslik_Datatable')
            if not baslik_table:
                logger.warning("Başlık tablosu bulunamadı")
                return results
            
            # Tablo satırlarını al
            tbody = baslik_table.find('tbody')
            if not tbody:
                logger.warning("Tbody bulunamadı")
                return results
                
            rows = tbody.find_all('tr')
            
            for row in rows:
                try:
                    cells = row.find_all('td')
                    if len(cells) < 2:
                        continue
                    
                    # İlk hücre: Mevzuat No
                    mevzuat_no_cell = cells[0]
                    mevzuat_no_link = mevzuat_no_cell.find('a')
                    if not mevzuat_no_link:
                        continue
                    
                    mevzuat_no = mevzuat_no_link.get_text(strip=True)
                    mevzuat_href = mevzuat_no_link.get('href', '')
                    
                    # İkinci hücre: Mevzuat Adı ve Detayları
                    mevzuat_ad_cell = cells[1]
                    mevzuat_ad_link = mevzuat_ad_cell.find('a')
                    if not mevzuat_ad_link:
                        continue
                    
                    # Başlığı al
                    title_div = mevzuat_ad_link.find('div')
                    if title_div:
                        title = self._clean_title(title_div.get_text(strip=True))
                    else:
                        title = self._clean_title(mevzuat_ad_link.get_text(strip=True))
                    
                    if not title:
                        continue
                    
                    # Detayları parse et
                    details = self._parse_details(mevzuat_ad_cell)
                    
                    # URL'i tam hale getir
                    full_url = urljoin(self.base_url, mevzuat_href)
                    
                    # URL'den parametreleri çıkar
                    url_params = self._extract_url_params(mevzuat_href)
                    
                    # PDF URL'lerini oluştur (iki format da)
                    pdf_urls = self._generate_pdf_urls(url_params, details.get('mevzuat_type', ''))
                    
                    # Sonuç oluştur
                    result = {
                        'title': title,
                        'url': full_url,
                        'mevzuat_type': details.get('mevzuat_type', 'Belirtilmemiş'),
                        'mevzuat_no': mevzuat_no,
                        'date': details.get('kabul_tarihi') or details.get('rg_tarihi', ''),
                        'rg_tarihi': details.get('rg_tarihi', ''),
                        'rg_sayisi': details.get('rg_sayisi', ''),
                        'tertip': details.get('tertip', ''),
                        'summary': f"{title[:150]}..." if len(title) > 150 else title,
                        'pdf_url': pdf_urls[0] if pdf_urls else '',  # İlk PDF URL'i
                        'pdf_urls': pdf_urls  # Tüm PDF URL'leri
                    }
                    
                    results.append(result)
                    
                except Exception as e:
                    logger.error(f"Satır parse hatası: {str(e)}")
                    continue
            
            logger.info(f"Parse tamamlandı: {len(results)} sonuç")
            return results
            
        except Exception as e:
            logger.error(f"HTML parse hatası: {str(e)}")
            return []
    
    def _parse_details(self, cell):
        """Hücredeki detayları parse et"""
        details = {}
        
        try:
            details_div = cell.find('div', class_='mt-1')
            if not details_div:
                return details
            
            details_html = str(details_div)
            details_text = details_div.get_text()
            
            # Mevzuat türü (ilk <i> tag)
            type_match = re.search(r'<i>([^<]+)</i>', details_html)
            if type_match:
                details['mevzuat_type'] = type_match.group(1).strip()
            
            # Tertip
            tertip_match = re.search(r'Tertip:\s*</b></i>\s*(\d+)', details_text)
            if tertip_match:
                details['tertip'] = tertip_match.group(1)
            
            # Resmî Gazete Tarihi
            rg_tarih_match = re.search(r'Resmî Gazete Tarihi:\s*</b></i>\s*([\d.]+)', details_text)
            if rg_tarih_match:
                details['rg_tarihi'] = rg_tarih_match.group(1)
            
            # Sayısı
            rg_sayi_match = re.search(r'Sayısı:\s*</b></i>\s*(\d+)', details_text)
            if rg_sayi_match:
                details['rg_sayisi'] = rg_sayi_match.group(1)
            
            # Kabul Tarihi
            kabul_tarih_match = re.search(r'Kabul Tarihi:\s*</b></i>\s*([\d.]+)', details_text)
            if kabul_tarih_match:
                details['kabul_tarihi'] = kabul_tarih_match.group(1)
            
        except Exception as e:
            logger.error(f"Detay parse hatası: {str(e)}")
        
        return details
    
    def _extract_url_params(self, href):
        """URL'den parametreleri çıkar"""
        params = {}
        
        # MevzuatNo
        mevzuat_no_match = re.search(r'MevzuatNo=(\d+)', href)
        if mevzuat_no_match:
            params['MevzuatNo'] = mevzuat_no_match.group(1)
        
        # MevzuatTur
        mevzuat_tur_match = re.search(r'MevzuatTur=(\d+)', href)
        if mevzuat_tur_match:
            params['MevzuatTur'] = mevzuat_tur_match.group(1)
        
        # MevzuatTertip
        mevzuat_tertip_match = re.search(r'MevzuatTertip=(\d+)', href)
        if mevzuat_tertip_match:
            params['MevzuatTertip'] = mevzuat_tertip_match.group(1)
        
        return params
    
    def _generate_pdf_urls(self, url_params, mevzuat_type_text):
        """PDF URL'lerini oluştur - iki format"""
        pdf_urls = []
        
        mevzuat_no = url_params.get('MevzuatNo')
        mevzuat_tur = url_params.get('MevzuatTur')
        mevzuat_tertip = url_params.get('MevzuatTertip')
        
        if not mevzuat_no:
            return pdf_urls
        
        # Format 1: Direkt PDF linki
        if mevzuat_tur and mevzuat_tertip:
            direct_pdf = f"{self.base_url}/MevzuatMetin/{mevzuat_tur}.{mevzuat_tertip}.{mevzuat_no}.pdf"
            pdf_urls.append(direct_pdf)
        
        # Format 2: Generate PDF linki
        # Mevzuat türünü metin olarak belirleme
        mevzuat_tur_text = self._get_mevzuat_tur_text(mevzuat_type_text, mevzuat_tur)
        
        generate_pdf = f"{self.base_url}/File/GeneratePdf?mevzuatNo={mevzuat_no}&mevzuatTur={mevzuat_tur_text}&mevzuatTertip={mevzuat_tertip}"
        pdf_urls.append(generate_pdf)
        
        return pdf_urls
    
    def _get_mevzuat_tur_text(self, mevzuat_type_text, mevzuat_tur_num):
        """Mevzuat türü numarasından metin çıkar"""
        # Önce mevcut metinden çıkarmaya çalış
        if mevzuat_type_text:
            type_lower = mevzuat_type_text.lower()
            if 'kanun' in type_lower:
                return 'Kanun'
            elif 'tebliğ' in type_lower or 'teblig' in type_lower:
                return 'Teblig'
            elif 'yönetmelik' in type_lower:
                return 'Yonetmelik'
            elif 'karar' in type_lower:
                return 'Karar'
            elif 'genelge' in type_lower:
                return 'Genelge'
            elif 'tüzük' in type_lower:
                return 'Tuzuk'
        
        # Numaradan çıkarmaya çalış
        if mevzuat_tur_num:
            tur_mapping = {
                '1': 'Kanun',
                '9': 'Teblig',
                '10': 'Yonetmelik',
                '20': 'Karar',
                '22': 'Genelge',
                '2': 'Tuzuk'
            }
            return tur_mapping.get(mevzuat_tur_num, 'Kanun')
        
        return 'Kanun'  # Varsayılan
    
    def _clean_title(self, title):
        """Başlığı temizle"""
        # HTML etiketlerini kaldır
        title = re.sub(r'<[^>]+>', '', title)
        # Fazla boşlukları kaldır
        title = ' '.join(title.split())
        return title.strip()
    
    def _empty_result(self, page, per_page, error=None):
        """Boş sonuç döndür"""
        result = {
            'results': [],
            'total_count': 0,
            'page': page,
            'per_page': per_page,
            'has_next': False,
            'has_previous': False,
            'source': 'mevzuat.gov.tr'
        }
        if error:
            result['error'] = error
        return result