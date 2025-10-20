# core/mevzuat_service.py
"""
Mevzuat.gov.tr arama servisi - mevzuat-mcp mantığıyla sıfırdan yazılmış
"""

import requests
from bs4 import BeautifulSoup
import logging
import json
from typing import Dict, List, Optional, Any
from urllib.parse import urlencode, urljoin
from django.shortcuts import render
from django.http import JsonResponse
from django.core.cache import cache
import re

logger = logging.getLogger(__name__)


class MevzuatService:
    """Mevzuat.gov.tr ile etkileşim servisi"""
    
    def __init__(self):
        self.base_url = "https://www.mevzuat.gov.tr"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'tr-TR,tr;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
    
    def search(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        Mevzuat ara
        
        Args:
            query: Arama metni veya mevzuat numarası
            **kwargs: Ek parametreler (type, page, etc.)
        
        Returns:
            Arama sonuçları
        """
        try:
            # Önbellek kontrolü
            cache_key = f"mevzuat_search_{query}_{kwargs.get('page', 1)}"
            cached = cache.get(cache_key)
            if cached:
                return cached
            
            # Arama yap
            results = self._perform_search(query, **kwargs)
            
            # Önbelleğe kaydet
            if results['success']:
                cache.set(cache_key, results, 300)  # 5 dakika
            
            return results
            
        except Exception as e:
            logger.error(f"Mevzuat search error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'results': [],
                'total': 0
            }
    
    def _perform_search(self, query: str, **kwargs) -> Dict[str, Any]:
        """Gerçek arama işlemi"""
        
        # Sayı mı kontrol et
        if query.strip().isdigit():
            # Direkt mevzuat numarası araması
            return self._search_by_number(query.strip())
        else:
            # Metin araması
            return self._search_by_text(query, **kwargs)
    
    def _search_by_number(self, number: str) -> Dict[str, Any]:
        """Mevzuat numarasına göre ara"""
        
        # Örnek URL'ler:
        # https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=6102
        # https://www.mevzuat.gov.tr/MevzuatMetin/1.5.6102.pdf
        
        url = f"{self.base_url}/mevzuat?MevzuatNo={number}"
        
        try:
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Başlık bul
                title = None
                title_elem = soup.find('title')
                if title_elem:
                    title_text = title_elem.get_text()
                    # "6102 sayılı Türk Ticaret Kanunu - Mevzuat" formatından temizle
                    if 'Mevzuat' in title_text:
                        title = title_text.replace(' - Mevzuat', '').strip()
                
                if not title or title == 'Mevzuat Bilgi Sistemi':
                    # Alternatif: h1, h2, h3 başlıkları
                    for tag in ['h1', 'h2', 'h3']:
                        header = soup.find(tag)
                        if header:
                            title = header.get_text(strip=True)
                            break
                
                if title and title != 'Mevzuat Bilgi Sistemi':
                    result = {
                        'mevzuat_no': number,
                        'title': title,
                        'url': url,
                        'pdf_url': f"{self.base_url}/MevzuatMetin/1.5.{number}.pdf",
                        'type': self._guess_type_from_title(title)
                    }
                    
                    return {
                        'success': True,
                        'results': [result],
                        'total': 1
                    }
            
        except Exception as e:
            logger.error(f"Number search error: {str(e)}")
        
        # Bulunamadı, normal arama yap
        return self._search_by_text(number)
    
    def _search_by_text(self, query: str, **kwargs) -> Dict[str, Any]:
        """Metin ile arama yap"""
        
        try:
            # Ana sayfadan token al
            main_resp = self.session.get(self.base_url)
            main_soup = BeautifulSoup(main_resp.text, 'html.parser')
            
            # Token bul
            token = None
            token_input = main_soup.find('input', {'name': 'antiforgerytoken'})
            if token_input:
                token = token_input.get('value')
            
            # Arama formunu gönder
            search_url = f"{self.base_url}/aramasonuc"
            
            form_data = {
                'AranacakMetin': query
            }
            
            if token:
                form_data['antiforgerytoken'] = token
            
            # POST isteği
            headers = self.session.headers.copy()
            headers.update({
                'Content-Type': 'application/x-www-form-urlencoded',
                'Referer': self.base_url,
                'Origin': self.base_url
            })
            
            response = self.session.post(
                search_url, 
                data=form_data, 
                headers=headers,
                timeout=15
            )
            
            if response.status_code == 200:
                return self._parse_search_results(response.text, query)
            
        except Exception as e:
            logger.error(f"Text search error: {str(e)}")
        
        return {
            'success': False,
            'error': 'Arama yapılamadı',
            'results': [],
            'total': 0
        }
    
    def _parse_search_results(self, html: str, query: str) -> Dict[str, Any]:
        """Arama sonuçlarını parse et"""
        
        soup = BeautifulSoup(html, 'html.parser')
        results = []
        
        # DataTable'ları bul
        tables = soup.find_all('table', id=lambda x: x and 'Datatable' in x)
        
        if not tables:
            # Alternatif: class ile ara
            tables = soup.find_all('table', class_=lambda x: x and 'table' in x)
        
        for table in tables:
            tbody = table.find('tbody')
            if not tbody:
                continue
            
            rows = tbody.find_all('tr')
            
            for row in rows:
                cells = row.find_all('td')
                if len(cells) < 2:
                    continue
                
                # İlk hücre: Mevzuat No
                no_cell = cells[0]
                no_link = no_cell.find('a')
                if not no_link:
                    continue
                
                mevzuat_no = no_link.get_text(strip=True)
                href = no_link.get('href', '')
                
                # İkinci hücre: Başlık ve detaylar
                title_cell = cells[1]
                title_link = title_cell.find('a')
                if not title_link:
                    continue
                
                # Başlık - ilk div
                title_div = title_link.find('div')
                if title_div:
                    # Highlight span'larını koru ama tag'leri temizle
                    title_html = str(title_div)
                    # <span style="background-color:yellow">...</span> kalıplarını koru
                    title_html = re.sub(r'<span[^>]*background-color:yellow[^>]*>([^<]*)</span>', r'<mark>\1</mark>', title_html)
                    # Diğer tüm HTML tag'lerini temizle
                    title = re.sub(r'<[^>]+>', '', title_html)
                    title = title.strip()
                else:
                    title = title_link.get_text(strip=True)
                
                # Detaylar - ikinci div
                details = {}
                details_div = title_link.find_all('div')[1] if len(title_link.find_all('div')) > 1 else None
                
                if details_div:
                    # Mevzuat türü
                    type_elem = details_div.find('i')
                    if type_elem:
                        details['type'] = type_elem.get_text(strip=True)
                    
                    # Detay metni
                    details_text = details_div.get_text()
                    
                    # Tertip
                    tertip_match = re.search(r'Tertip:\s*(\d+)', details_text)
                    if tertip_match:
                        details['tertip'] = tertip_match.group(1)
                    
                    # RG Tarihi
                    rg_date_match = re.search(r'Resmî Gazete Tarihi:\s*([\d.]+)', details_text)
                    if rg_date_match:
                        details['rg_date'] = rg_date_match.group(1)
                    
                    # RG Sayısı
                    rg_no_match = re.search(r'Sayısı:\s*(\d+)', details_text)
                    if rg_no_match:
                        details['rg_no'] = rg_no_match.group(1)
                    
                    # Kabul Tarihi
                    accept_date_match = re.search(r'Kabul Tarihi:\s*([\d.]+)', details_text)
                    if accept_date_match:
                        details['accept_date'] = accept_date_match.group(1)
                
                # URL'den parametreleri çıkar
                params = {}
                if '?' in href:
                    param_str = href.split('?')[1]
                    for param in param_str.split('&'):
                        if '=' in param:
                            key, value = param.split('=', 1)
                            params[key] = value
                
                # Sonuç oluştur
                result = {
                    'mevzuat_no': mevzuat_no,
                    'title': title,
                    'url': urljoin(self.base_url, href),
                    'type': details.get('type', 'Belirtilmemiş'),
                    'tertip': params.get('MevzuatTertip', details.get('tertip', '')),
                    'rg_date': details.get('rg_date', ''),
                    'rg_no': details.get('rg_no', ''),
                    'accept_date': details.get('accept_date', ''),
                    'pdf_url': self._generate_pdf_url(params, details)
                }
                
                results.append(result)
        
        return {
            'success': True,
            'results': results,
            'total': len(results),
            'query': query
        }
    
    def _generate_pdf_url(self, params: Dict[str, str], details: Dict[str, str]) -> str:
        """PDF URL oluştur"""
        
        mevzuat_no = params.get('MevzuatNo', '')
        mevzuat_tur = params.get('MevzuatTur', '1')
        mevzuat_tertip = params.get('MevzuatTertip', '5')
        
        if mevzuat_no:
            # Format: /MevzuatMetin/{tur}.{tertip}.{no}.pdf
            return f"{self.base_url}/MevzuatMetin/{mevzuat_tur}.{mevzuat_tertip}.{mevzuat_no}.pdf"
        
        return ''
    
    def _guess_type_from_title(self, title: str) -> str:
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


# Django view fonksiyonları
def legislation_home(request):
    """Mevzuat ana sayfası"""
    return render(request, 'core/legislation_home.html')


def legislation_search(request):
    """Mevzuat arama - AJAX endpoint"""
    
    if request.method == 'GET':
        query = request.GET.get('q', '').strip()
        page = int(request.GET.get('page', 1))
        
        if not query:
            return JsonResponse({
                'success': False,
                'error': 'Arama terimi giriniz',
                'results': [],
                'total': 0
            })
        
        # Servis ile arama yap
        service = MevzuatService()
        result = service.search(query, page=page)
        
        return JsonResponse(result)
    
    return JsonResponse({'error': 'Invalid method'}, status=400)


def legislation_results(request):
    """Mevzuat arama sonuçları sayfası"""
    
    query = request.GET.get('q', '').strip()
    page = int(request.GET.get('page', 1))
    
    if not query:
        return render(request, 'core/legislation_results.html', {
            'query': '',
            'results': [],
            'error': 'Arama terimi giriniz'
        })
    
    # Servis ile arama yap
    service = MevzuatService()
    search_result = service.search(query, page=page)
    
    # Template'e gönder
    context = {
        'query': query,
        'results': search_result.get('results', []),
        'total_count': search_result.get('total', 0),
        'page': page,
        'has_results': len(search_result.get('results', [])) > 0,
        'error': search_result.get('error') if not search_result.get('success') else None
    }
    
    return render(request, 'core/legislation_results.html', context)


def mevzuat_detail(request, mevzuat_no):
    """Mevzuat detay sayfası"""
    
    service = MevzuatService()
    result = service.search(mevzuat_no)
    
    if result.get('success') and result.get('results'):
        mevzuat = result['results'][0]
        return render(request, 'core/mevzuat_detail.html', {
            'mevzuat': mevzuat
        })
    
    return render(request, 'core/mevzuat_detail.html', {
        'error': 'Mevzuat bulunamadı'
    })