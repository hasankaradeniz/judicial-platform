# Profesyonel Mevzuat.gov.tr Scraping Sistemi
"""
Bu sistem mevzuat.gov.tr'den tüm mevzuatları otomatik olarak çeker ve veritabanına kaydeder.

Özellikler:
- Tüm kanun, yönetmelik, tebliğ listesi
- Madde bazında içerik parsing
- Rate limiting ve bot koruması bypass
- Otomatik retry ve hata yönetimi
- Güncellemeleri takip etme
"""

import requests
from bs4 import BeautifulSoup
import time
import random
import logging
from urllib.parse import urljoin, urlparse
from datetime import datetime, timedelta
import json
import re
from dataclasses import dataclass
from typing import List, Optional, Dict
import concurrent.futures
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Django imports (runtime'da import edilecek)
# from core.models import ProfessionalLegislation, LegislationArticle, LegislationType, LegislationCategory

@dataclass
class MevzuatInfo:
    """Mevzuat bilgi yapısı"""
    title: str
    number: str
    type: str
    url: str
    pdf_url: str = ""
    rg_date: str = ""
    rg_number: str = ""
    effective_date: str = ""
    articles: List[Dict] = None
    
    def __post_init__(self):
        if self.articles is None:
            self.articles = []

class MevzuatScraper:
    """Ana scraper sınıfı"""
    
    def __init__(self):
        self.base_url = "https://www.mevzuat.gov.tr"
        self.session = self._create_session()
        self.logger = self._setup_logging()
        
        # Rate limiting
        self.request_delay = 1.0  # Her istek arasında 1 saniye bekle
        self.max_retries = 3
        
        # Cache
        self.scraped_urls = set()
        self.failed_urls = set()
        
    def _create_session(self) -> requests.Session:
        """Gelişmiş session oluştur"""
        session = requests.Session()
        
        # Retry stratejisi
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            method_whitelist=["HEAD", "GET", "OPTIONS"],
            backoff_factor=1
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Human-like headers
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'Connection': 'keep-alive'
        })
        
        return session
    
    def _setup_logging(self) -> logging.Logger:
        """Logging ayarla"""
        logger = logging.getLogger('mevzuat_scraper')
        logger.setLevel(logging.INFO)
        
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    def _random_delay(self):
        """Random gecikme ekle"""
        delay = self.request_delay + random.uniform(0.5, 2.0)
        time.sleep(delay)
    
    def _safe_request(self, url: str, **kwargs) -> Optional[requests.Response]:
        """Güvenli HTTP isteği"""
        if url in self.failed_urls:
            return None
            
        for attempt in range(self.max_retries):
            try:
                self.logger.info(f"İstek gönderiliyor: {url} (Deneme {attempt + 1})")
                response = self.session.get(url, timeout=15, **kwargs)
                
                if response.status_code == 200:
                    self.scraped_urls.add(url)
                    return response
                elif response.status_code == 429:
                    # Rate limit aşıldı, daha uzun bekle
                    wait_time = (attempt + 1) * 5
                    self.logger.warning(f"Rate limit aşıldı, {wait_time}s bekleniyor...")
                    time.sleep(wait_time)
                else:
                    self.logger.warning(f"HTTP {response.status_code}: {url}")
                    
            except Exception as e:
                self.logger.error(f"İstek hatası {url}: {str(e)}")
                time.sleep((attempt + 1) * 2)
        
        self.failed_urls.add(url)
        return None
    
    def get_legislation_list(self) -> List[MevzuatInfo]:
        """Ana mevzuat listesini çek"""
        self.logger.info("🚀 Mevzuat listesi çekiliyor...")
        
        legislation_list = []
        
        # Farklı mevzuat türlerini tara
        search_urls = [
            f"{self.base_url}/aramasonuc?MevzuatTurId=1",  # Kanunlar
            f"{self.base_url}/aramasonuc?MevzuatTurId=2",  # Tüzükler  
            f"{self.base_url}/aramasonuc?MevzuatTurId=3",  # Yönetmelikler
            f"{self.base_url}/aramasonuc?MevzuatTurId=4",  # Tebliğler
            f"{self.base_url}/aramasonuc?MevzuatTurId=5",  # Genelgeler
            f"{self.base_url}/aramasonuc?MevzuatTurId=6",  # CBK
        ]
        
        for url in search_urls:
            self._random_delay()
            response = self._safe_request(url)
            
            if response:
                soup = BeautifulSoup(response.text, 'html.parser')
                items = self._parse_legislation_list_page(soup)
                legislation_list.extend(items)
                self.logger.info(f"✅ {len(items)} mevzuat bulundu: {url}")
                
                # Sayfalama varsa diğer sayfaları da çek
                pagination_links = self._get_pagination_links(soup)
                for page_url in pagination_links[:10]:  # İlk 10 sayfa
                    self._random_delay()
                    page_response = self._safe_request(page_url)
                    if page_response:
                        page_soup = BeautifulSoup(page_response.text, 'html.parser')
                        page_items = self._parse_legislation_list_page(page_soup)
                        legislation_list.extend(page_items)
                        self.logger.info(f"✅ Sayfa işlendi: {len(page_items)} item")
            else:
                self.logger.error(f"❌ Liste çekilemedi: {url}")
        
        self.logger.info(f"🎉 Toplam {len(legislation_list)} mevzuat bulundu")
        return legislation_list
    
    def _parse_legislation_list_page(self, soup: BeautifulSoup) -> List[MevzuatInfo]:
        """Liste sayfasındaki mevzuatları parse et"""
        items = []
        
        # DataTable satırlarını bul
        table_rows = soup.select('table tbody tr')
        
        for row in table_rows:
            try:
                cells = row.find_all('td')
                if len(cells) < 2:
                    continue
                
                # İlk hücre: Numara ve link
                number_cell = cells[0]
                number_link = number_cell.find('a')
                if not number_link:
                    continue
                
                number = number_link.get_text(strip=True)
                detail_url = urljoin(self.base_url, number_link.get('href', ''))
                
                # İkinci hücre: Başlık ve detaylar
                title_cell = cells[1]
                title_link = title_cell.find('a')
                if not title_link:
                    continue
                
                # Başlık
                title_div = title_link.find('div')
                title = title_div.get_text(strip=True) if title_div else title_link.get_text(strip=True)
                
                # Tür bilgisi
                details_div = title_link.find_all('div')[1] if len(title_link.find_all('div')) > 1 else None
                legislation_type = "Kanun"  # Default
                rg_date = ""
                rg_number = ""
                
                if details_div:
                    details_text = details_div.get_text()
                    
                    # Tür
                    if 'Yönetmelik' in details_text:
                        legislation_type = "Yönetmelik"
                    elif 'Tebliğ' in details_text:
                        legislation_type = "Tebliğ"
                    elif 'Genelge' in details_text:
                        legislation_type = "Genelge"
                    elif 'Tüzük' in details_text:
                        legislation_type = "Tüzük"
                    
                    # RG Tarihi
                    rg_date_match = re.search(r'Resmî Gazete Tarihi:\s*([0-9.]+)', details_text)
                    if rg_date_match:
                        rg_date = rg_date_match.group(1)
                    
                    # RG Sayısı  
                    rg_number_match = re.search(r'Sayısı:\s*(\d+)', details_text)
                    if rg_number_match:
                        rg_number = rg_number_match.group(1)
                
                # PDF URL oluştur
                pdf_url = f"{self.base_url}/MevzuatMetin/1.5.{number}.pdf"
                
                item = MevzuatInfo(
                    title=title,
                    number=number,
                    type=legislation_type,
                    url=detail_url,
                    pdf_url=pdf_url,
                    rg_date=rg_date,
                    rg_number=rg_number
                )
                
                items.append(item)
                
            except Exception as e:
                self.logger.error(f"Satır parse hatası: {str(e)}")
                continue
        
        return items
    
    def _get_pagination_links(self, soup: BeautifulSoup) -> List[str]:
        """Sayfalama linklerini bul"""
        pagination_links = []
        
        # Sayfalama linklerini ara
        pagination = soup.find('div', class_='pagination') or soup.find('nav')
        if pagination:
            links = pagination.find_all('a', href=True)
            for link in links:
                href = link.get('href')
                if href and 'page=' in href:
                    full_url = urljoin(self.base_url, href)
                    pagination_links.append(full_url)
        
        return pagination_links[:10]  # İlk 10 sayfa
    
    def scrape_legislation_content(self, mevzuat: MevzuatInfo) -> MevzuatInfo:
        """Belirli bir mevzuatın içeriğini çek"""
        self.logger.info(f"📖 İçerik çekiliyor: {mevzuat.title} ({mevzuat.number})")
        
        self._random_delay()
        response = self._safe_request(mevzuat.url)
        
        if not response:
            self.logger.error(f"❌ İçerik çekilemedi: {mevzuat.url}")
            return mevzuat
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Maddeleri parse et
        articles = self._parse_articles(soup)
        mevzuat.articles = articles
        
        # Ek bilgiler
        mevzuat.effective_date = self._extract_effective_date(soup)
        
        self.logger.info(f"✅ {len(articles)} madde bulundu: {mevzuat.title}")
        return mevzuat
    
    def _parse_articles(self, soup: BeautifulSoup) -> List[Dict]:
        """Maddeleri parse et"""
        articles = []
        
        # Farklı madde formatlarını dene
        article_selectors = [
            '.madde',
            '.article',
            '[id*="madde"]',
            'p:contains("Madde")',
            'div:contains("MADDE")',
            'h3:contains("Madde")',
        ]
        
        for selector in article_selectors:
            try:
                elements = soup.select(selector)
                if elements:
                    self.logger.info(f"Madde bulundu: {selector} - {len(elements)} adet")
                    
                    for element in elements:
                        article = self._parse_single_article(element)
                        if article:
                            articles.append(article)
                    break
            except:
                continue
        
        # Fallback: Tüm metni tara
        if not articles:
            articles = self._parse_articles_fallback(soup)
        
        return articles
    
    def _parse_single_article(self, element) -> Optional[Dict]:
        """Tek maddeyi parse et"""
        try:
            text = element.get_text(strip=True)
            
            # Madde numarasını bul
            article_match = re.search(r'(?:MADDE|Madde)\s*[-–]?\s*(\d+)', text, re.IGNORECASE)
            if not article_match:
                return None
            
            article_number = article_match.group(1)
            
            # Başlık bul (opsiyonel)
            title = ""
            title_match = re.search(r'(?:MADDE|Madde)\s*[-–]?\s*\d+\s*[-–]?\s*([^\n]+)', text, re.IGNORECASE)
            if title_match:
                title = title_match.group(1).strip()
            
            # Madde metnini ayıkla
            content = re.sub(r'(?:MADDE|Madde)\s*[-–]?\s*\d+.*?\n', '', text, flags=re.IGNORECASE).strip()
            
            return {
                'number': article_number,
                'title': title,
                'text': content,
                'order': int(article_number)
            }
            
        except Exception as e:
            self.logger.error(f"Madde parse hatası: {str(e)}")
            return None
    
    def _parse_articles_fallback(self, soup: BeautifulSoup) -> List[Dict]:
        """Fallback madde parsing"""
        articles = []
        
        # Tüm metni al ve madde kalıplarını ara
        all_text = soup.get_text()
        
        # Madde kalıpları
        article_pattern = r'(?:MADDE|Madde)\s*[-–]?\s*(\d+)\s*[-–]?\s*([^\n]*)\n(.*?)(?=(?:MADDE|Madde)\s*[-–]?\s*\d+|$)'
        
        matches = re.finditer(article_pattern, all_text, re.IGNORECASE | re.DOTALL)
        
        for match in matches:
            article_number = match.group(1)
            title = match.group(2).strip()
            content = match.group(3).strip()
            
            if content:
                articles.append({
                    'number': article_number,
                    'title': title,
                    'text': content[:2000],  # İlk 2000 karakter
                    'order': int(article_number)
                })
        
        return articles
    
    def _extract_effective_date(self, soup: BeautifulSoup) -> str:
        """Yürürlük tarihini çıkar"""
        text = soup.get_text()
        
        # Yürürlük tarih kalıpları
        patterns = [
            r'yürürlü[kğ]e?\s+gir.*?(\d{1,2}[./]\d{1,2}[./]\d{4})',
            r'yürürül[üu]k.*?(\d{1,2}[./]\d{1,2}[./]\d{4})',
            r'(\d{1,2}[./]\d{1,2}[./]\d{4}).*?yürürlü[kğ]e'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return ""

# Django Management Command Wrapper
def save_to_database(mevzuat_list: List[MevzuatInfo]):
    """Mevzuatları veritabanına kaydet"""
    from core.models import ProfessionalLegislation, LegislationArticle, LegislationType, LegislationCategory
    from django.utils.text import slugify
    
    saved_count = 0
    updated_count = 0
    
    for mevzuat in mevzuat_list:
        try:
            # Mevzuat türünü bul/oluştur
            legislation_type, _ = LegislationType.objects.get_or_create(
                code=mevzuat.type.lower(),
                defaults={
                    'name': mevzuat.type,
                    'hierarchy_level': 2,
                    'display_order': 0
                }
            )
            
            # Mevzuat oluştur/güncelle
            legislation, created = ProfessionalLegislation.objects.get_or_create(
                number=mevzuat.number,
                defaults={
                    'title': mevzuat.title,
                    'legislation_type': legislation_type,
                    'official_gazette_number': mevzuat.rg_number,
                    'source_url': mevzuat.url,
                    'pdf_url': mevzuat.pdf_url,
                    'status': 'active',
                    'mevzuat_gov_id': mevzuat.number
                }
            )
            
            if created:
                saved_count += 1
                print(f"✅ Yeni mevzuat: {mevzuat.title}")
            else:
                updated_count += 1
                print(f"🔄 Güncellendi: {mevzuat.title}")
            
            # Maddeleri kaydet
            if mevzuat.articles:
                # Mevcut maddeleri sil
                legislation.articles.all().delete()
                
                # Yeni maddeleri ekle
                for article_data in mevzuat.articles:
                    LegislationArticle.objects.create(
                        legislation=legislation,
                        article_number=article_data['number'],
                        title=article_data.get('title', ''),
                        text=article_data['text'],
                        order=article_data.get('order', 0)
                    )
                
                print(f"  📖 {len(mevzuat.articles)} madde eklendi")
            
        except Exception as e:
            print(f"❌ Kayıt hatası: {mevzuat.title} - {str(e)}")
    
    print(f"\n🎉 İşlem tamamlandı!")
    print(f"📊 {saved_count} yeni mevzuat")
    print(f"🔄 {updated_count} güncellenen mevzuat")

# Ana çalıştırma fonksiyonu
def run_full_scrape():
    """Tam scraping işlemini çalıştır"""
    scraper = MevzuatScraper()
    
    print("🚀 Mevzuat scraping başlıyor...")
    
    # 1. Mevzuat listesini çek
    legislation_list = scraper.get_legislation_list()
    
    if not legislation_list:
        print("❌ Mevzuat listesi çekilemedi!")
        return
    
    print(f"📋 {len(legislation_list)} mevzuat bulundu")
    
    # 2. İlk 50 mevzuatın içeriğini çek (test için)
    print("📖 İçerikler çekiliyor...")
    
    for i, mevzuat in enumerate(legislation_list[:50], 1):
        print(f"[{i}/50] İşleniyor: {mevzuat.title}")
        
        try:
            mevzuat_with_content = scraper.scrape_legislation_content(mevzuat)
            legislation_list[i-1] = mevzuat_with_content
            
            # Her 10 mevzuattan sonra veritabanına kaydet
            if i % 10 == 0:
                save_to_database(legislation_list[i-10:i])
                print(f"💾 {i} mevzuat işlendi ve kaydedildi")
                
        except Exception as e:
            print(f"❌ Hata: {mevzuat.title} - {str(e)}")
            continue
    
    # Kalanları kaydet
    remaining = len(legislation_list) % 10
    if remaining > 0:
        save_to_database(legislation_list[-remaining:])
    
    print("🎉 Scraping tamamlandı!")

if __name__ == "__main__":
    run_full_scrape()