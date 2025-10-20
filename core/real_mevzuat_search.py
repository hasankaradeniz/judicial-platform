import os
import time
import re
import requests
from bs4 import BeautifulSoup
from django.core.cache import cache
import logging
import urllib.parse

logger = logging.getLogger(__name__)

class RealMevzuatSearcher:
    """Gerçek mevzuat.gov.tr arama sistemi - canlı sonuçlar"""
    
    def __init__(self):
        self.base_url = "https://www.mevzuat.gov.tr"
        
    def search_legislation(self, query, mevzuat_type=None, page=1, per_page=20):
        """Ana arama fonksiyonu - gerçek mevzuat.gov.tr sonuçları"""
        try:
            # Cache kontrolü
            cache_key = f"real_search_{query}_{mevzuat_type}_{page}".replace(' ', '_')
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.info(f"Cache'den sonuç: {query}")
                return cached_result
            
            # Requests ile POST arama
            results = self._search_with_requests(query, mevzuat_type, page, per_page)
            
            # Cache'e kaydet
            if results and results['total_count'] > 0:
                cache.set(cache_key, results, 1800)  # 30 dakika
                
            return results
            
        except Exception as e:
            logger.error(f"Search error: {str(e)}")
            return {
                'results': [],
                'total_count': 0,
                'page': page,
                'per_page': per_page,
                'has_next': False,
                'has_previous': False,
                'error': str(e)
            }
    
    def _search_with_requests(self, query, mevzuat_type, page, per_page):
        """Requests ile mevzuat.gov.tr'de POST arama"""
        try:
            # Session oluştur
            session = requests.Session()
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'tr-TR,tr;q=0.8,en-US;q=0.5,en;q=0.3',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            session.headers.update(headers)
            
            logger.info("Ana sayfa ziyaret ediliyor...")
            
            # Ana sayfayı ziyaret et
            main_response = session.get("https://www.mevzuat.gov.tr/", timeout=15)
            
            if main_response.status_code != 200:
                logger.error(f"Ana sayfa hatası: {main_response.status_code}")
                return None
            
            # Anti-forgery token'ı bul
            soup = BeautifulSoup(main_response.content, 'html.parser')
            antiforgery_input = soup.find('input', {'name': 'antiforgerytoken'})
            antiforgery_token = antiforgery_input.get('value', '') if antiforgery_input else ''
            
            logger.info(f"Antiforgery token alındı: {antiforgery_token[:20]}...")
            
            # POST için headers güncelle
            post_headers = headers.copy()
            post_headers.update({
                'Content-Type': 'application/x-www-form-urlencoded',
                'Referer': 'https://www.mevzuat.gov.tr/',
                'Origin': 'https://www.mevzuat.gov.tr'
            })
            
            # POST verisi hazırla
            post_data = {
                'AranacakMetin': query,
                'antiforgerytoken': antiforgery_token
            }
            
            logger.info(f"Arama yapılıyor: '{query}'")
            
            # POST isteği gönder
            search_response = session.post(
                "https://www.mevzuat.gov.tr/aramasonuc",
                data=post_data,
                headers=post_headers,
                timeout=20,
                allow_redirects=True
            )
            
            if search_response.status_code != 200:
                logger.error(f"Arama POST hatası: {search_response.status_code}")
                return None
            
            logger.info("Arama başarılı, sonuçlar parse ediliyor...")
            
            # HTML'i parse et
            results = self._parse_search_results(search_response.text, query, page, per_page)
            
            if results and results['total_count'] > 0:
                logger.info(f"Toplam {results['total_count']} sonuç bulundu")
                return results
            else:
                logger.warning("Arama sonuç vermedi")
                return None
                
        except Exception as e:
            logger.error(f"Requests arama hatası: {str(e)}")
            return None
    
    def _parse_search_results(self, html_content, query, page, per_page):
        """HTML sonuçlarını parse et"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            results = []
            
            logger.info("HTML sonuçları parse ediliyor...")
            
            # Debug: HTML'in bir kısmını log'la ve dosyaya kaydet
            if len(html_content) > 1000:
                logger.info(f"HTML içerik uzunluğu: {len(html_content)} karakter")
                
                # HTML'i debug için dosyaya kaydet
                try:
                    with open('/tmp/mevzuat_search_debug.html', 'w', encoding='utf-8') as f:
                        f.write(html_content)
                    logger.info("HTML debug dosyası kaydedildi: /tmp/mevzuat_search_debug.html")
                except:
                    pass
                
                # HTML'de hangi elementlerin olduğunu kontrol et
                table_count = html_content.count('<table')
                datatable_count = html_content.count('Baslik_Datatable')
                mevzuat_count = html_content.count('MevzuatNo=')
                tbody_count = html_content.count('<tbody')
                
                logger.info(f"HTML analizi - Table: {table_count}, DataTable: {datatable_count}, MevzuatNo: {mevzuat_count}, tbody: {tbody_count}")
                
                # İlk 2000 karakteri log'la
                logger.info(f"HTML başlangıcı: {html_content[:2000]}")
            
            # 1. DataTable sonuçlarını ara
            datatable = soup.find('table', {'id': 'Baslik_Datatable'})
            
            if datatable:
                logger.info("Baslik_Datatable bulundu")
                tbody = datatable.find('tbody')
                
                if tbody:
                    rows = tbody.find_all('tr')
                    logger.info(f"Tablo satırları: {len(rows)}")
                    
                    for i, row in enumerate(rows):
                        try:
                            result = self._parse_table_row(row, query)
                            if result:
                                results.append(result)
                                logger.info(f"Satır {i+1} parse edildi: {result['title'][:50]}...")
                        except Exception as e:
                            logger.warning(f"Satır {i+1} parse hatası: {str(e)}")
                            continue
            
            # 2. Eğer DataTable yoksa div sonuçları ara
            if not results:
                logger.info("DataTable bulunamadı, div sonuçları aranıyor...")
                
                # Mevzuat linklerini ara
                mevzuat_links = soup.find_all('a', href=re.compile(r'mevzuat\?MevzuatNo=\d+'))
                
                for link in mevzuat_links:
                    try:
                        result = self._parse_link_result(link, query)
                        if result and result not in results:
                            results.append(result)
                            logger.info(f"Link parse edildi: {result['title'][:50]}...")
                    except Exception as e:
                        logger.warning(f"Link parse hatası: {str(e)}")
                        continue
            
            # 3. Genel tablo arama
            if not results:
                logger.info("Özel parse başarısız, genel tablo aranıyor...")
                
                tables = soup.find_all('table')
                for table in tables:
                    rows = table.find_all('tr')
                    for row in rows:
                        links = row.find_all('a', href=True)
                        for link in links:
                            href = link.get('href', '')
                            if 'MevzuatNo=' in href and 'fihristi' not in href.lower():
                                try:
                                    result = self._parse_link_result(link, query)
                                    if result and result not in results:
                                        results.append(result)
                                except:
                                    continue
            
            # Sonuçları filtrele ve düzenle
            filtered_results = self._filter_and_clean_results(results, query)
            
            logger.info(f"Filtreleme sonrası: {len(filtered_results)} sonuç")
            
            # Eğer hiç sonuç yoksa ve HTML'de mevzuat linkleri varsa, emergency parse yap
            if not filtered_results and html_content.count('MevzuatNo=') > 0:
                logger.info("Emergency parse başlatılıyor...")
                emergency_results = self._emergency_parse(html_content, query)
                if emergency_results:
                    filtered_results = emergency_results
                    logger.info(f"Emergency parse: {len(filtered_results)} sonuç")
            
            # Sayfalama
            total_count = len(filtered_results)
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            paginated_results = filtered_results[start_idx:end_idx]
            
            return {
                'results': paginated_results,
                'total_count': total_count,
                'page': page,
                'per_page': per_page,
                'has_next': end_idx < total_count,
                'has_previous': page > 1,
                'source': 'real_mevzuat.gov.tr'
            }
            
        except Exception as e:
            logger.error(f"HTML parse hatası: {str(e)}")
            return {
                'results': [],
                'total_count': 0,
                'page': page,
                'per_page': per_page,
                'has_next': False,
                'has_previous': False,
                'error': str(e)
            }
    
    def _parse_table_row(self, row, query):
        """Tablo satırını parse et"""
        try:
            cells = row.find_all('td')
            if len(cells) < 2:
                return None
            
            # İlk hücre: Mevzuat No
            no_cell = cells[0]
            mevzuat_no = ""
            no_link = no_cell.find('a', href=True)
            if no_link:
                mevzuat_no = no_link.get_text(strip=True)
                href = no_link.get('href', '')
            
            # İkinci hücre: Mevzuat Adı
            title_cell = cells[1]
            main_link = title_cell.find('a', href=True)
            
            if not main_link:
                return None
            
            # Başlık
            title_div = main_link.find('div')
            if title_div:
                # HTML elementlerini temizle
                title = self._clean_html_text(title_div)
            else:
                title = main_link.get_text(strip=True)
            
            # URL
            href = main_link.get('href', '')
            if href.startswith('/'):
                full_url = self.base_url + href
            elif not href.startswith('http'):
                full_url = self.base_url + '/' + href
            else:
                full_url = href
            
            # Meta bilgiler
            meta_div = main_link.find('div', class_='mt-1 small')
            type_info = ""
            rg_date = ""
            rg_number = ""
            
            if meta_div:
                meta_text = meta_div.get_text()
                
                # Tür
                if 'Kanunlar' in meta_text:
                    type_info = "Kanun"
                elif 'Yönetmelik' in meta_text:
                    type_info = "Yönetmelik"
                elif 'Tüzük' in meta_text:
                    type_info = "Tüzük"
                elif 'Kararname' in meta_text:
                    type_info = "Kararname"
                
                # RG tarihi
                rg_match = re.search(r'Resmî Gazete Tarihi:\s*([0-9.]+)', meta_text)
                if rg_match:
                    rg_date = rg_match.group(1).strip()
                
                # RG sayısı
                sayi_match = re.search(r'Sayısı:\s*([0-9]+)', meta_text)
                if sayi_match:
                    rg_number = sayi_match.group(1).strip()
            
            # Önceki metinler kontrolü
            has_previous = len(cells) >= 3 and bool(cells[2].find('button'))
            
            # Kendi sistemimizde PDF göstermek için URL
            internal_pdf_url = f"/mevzuat/pdf/?MevzuatNo={mevzuat_no}&MevzuatTur=1&MevzuatTertip=5"
            
            return {
                'title': title,
                'url': internal_pdf_url,  # Kendi sistemimizde açılacak
                'external_url': full_url,  # Dış link
                'mevzuat_no': mevzuat_no,
                'type': type_info or 'Mevzuat',
                'rg_date': rg_date,
                'rg_number': rg_number,
                'source': 'real_mevzuat.gov.tr',
                'has_previous_versions': has_previous,
                'search_query': query
            }
            
        except Exception as e:
            logger.error(f"Satır parse hatası: {str(e)}")
            return None
    
    def _parse_link_result(self, link, query):
        """Link sonucunu parse et"""
        try:
            href = link.get('href', '')
            title = self._clean_html_text(link)
            
            if not href or not title:
                return None
            
            # URL düzenle
            if href.startswith('/'):
                full_url = self.base_url + href
            elif not href.startswith('http'):
                full_url = self.base_url + '/' + href
            else:
                full_url = href
            
            # Mevzuat numarasını çıkar
            mevzuat_no = ""
            match = re.search(r'MevzuatNo[=/](\d+)', href)
            if match:
                mevzuat_no = match.group(1)
            
            # Kendi sistemimizde PDF göstermek için URL
            internal_pdf_url = f"/mevzuat/pdf/?MevzuatNo={mevzuat_no}&MevzuatTur=1&MevzuatTertip=5" if mevzuat_no else full_url
            
            return {
                'title': title,
                'url': internal_pdf_url,  # Kendi sistemimizde açılacak
                'external_url': full_url,  # Dış link
                'mevzuat_no': mevzuat_no,
                'type': 'Mevzuat',
                'rg_date': '',
                'rg_number': '',
                'source': 'real_mevzuat.gov.tr',
                'has_previous_versions': bool(mevzuat_no),
                'search_query': query
            }
            
        except Exception as e:
            logger.error(f"Link parse hatası: {str(e)}")
            return None
    
    def _clean_html_text(self, element):
        """HTML elementinden temiz metin çıkar"""
        if not element:
            return ""
        
        # Span elementlerini koru ama içeriği al
        for span in element.find_all('span'):
            span.replace_with(span.get_text())
        
        # Temiz metin al
        text = element.get_text(separator=' ', strip=True)
        
        # Çoklu boşlukları temizle
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def _filter_and_clean_results(self, results, query):
        """Sonuçları filtrele ve temizle"""
        filtered = []
        seen_titles = set()
        
        for result in results:
            title = result.get('title', '').strip()
            
            # Boş başlık atla
            if not title or len(title) < 5:
                continue
            
            # Fihristi atla
            if any(word in title.lower() for word in ['fihristi', 'indeks', 'navigation']):
                continue
            
            # Aynı başlığı tekrar ekleme
            if title in seen_titles:
                continue
            
            seen_titles.add(title)
            filtered.append(result)
        
        return filtered
    
    def _emergency_parse(self, html_content, query):
        """Emergency parsing - en basit yöntemle sonuçları bul"""
        try:
            import re
            results = []
            
            logger.info("Emergency parsing başlıyor...")
            
            # Tüm MevzuatNo linklerini bul
            mevzuat_pattern = r'href=["\']([^"\']*MevzuatNo=(\d+)[^"\']*)["\'][^>]*>([^<]+)<'
            matches = re.finditer(mevzuat_pattern, html_content, re.IGNORECASE)
            
            seen_numbers = set()
            
            for match in matches:
                href = match.group(1)
                mevzuat_no = match.group(2)
                title = match.group(3).strip()
                
                # Duplicate kontrolü
                if mevzuat_no in seen_numbers:
                    continue
                seen_numbers.add(mevzuat_no)
                
                # Fihristi atla
                if 'fihristi' in title.lower():
                    continue
                
                # Çok kısa başlıkları atla
                if len(title) < 10:
                    continue
                
                # URL düzelt
                if href.startswith('/'):
                    full_url = self.base_url + href
                elif not href.startswith('http'):
                    full_url = self.base_url + '/' + href
                else:
                    full_url = href
                
                # Kendi sistemimizde PDF göstermek için URL
                internal_pdf_url = f"/mevzuat/pdf/?MevzuatNo={mevzuat_no}&MevzuatTur=1&MevzuatTertip=5"
                
                result = {
                    'title': title,
                    'url': internal_pdf_url,
                    'external_url': full_url,
                    'mevzuat_no': mevzuat_no,
                    'type': 'Mevzuat',
                    'rg_date': '',
                    'rg_number': '',
                    'source': 'emergency_parse',
                    'has_previous_versions': True,
                    'search_query': query
                }
                
                results.append(result)
                logger.info(f"Emergency parse buldu: {title[:50]}... (No: {mevzuat_no})")
            
            logger.info(f"Emergency parse toplam: {len(results)} sonuç")
            return results
            
        except Exception as e:
            logger.error(f"Emergency parse hatası: {str(e)}")
            return []

# Kullanım için alias
SimpleMevzuatSearcher = RealMevzuatSearcher