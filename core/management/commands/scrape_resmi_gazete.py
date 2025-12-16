import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import logging
import time
import re
from django.core.management.base import BaseCommand
from django.conf import settings
import os

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Resmi Gazete günlük içeriklerini scrape eder'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='Belirli bir tarih için scrape (YYYY-MM-DD formatında)'
        )
        parser.add_argument(
            '--output',
            type=str,
            help='Çıktı dosya yolu (opsiyonel)'
        )

    def handle(self, *args, **options):
        target_date = options['date']
        if target_date:
            try:
                target_date = datetime.strptime(target_date, '%Y-%m-%d').date()
            except ValueError:
                self.stdout.write(
                    self.style.ERROR('Hatalı tarih formatı. YYYY-MM-DD kullanın.')
                )
                return
        else:
            target_date = datetime.now().date()

        self.stdout.write(f'Resmi Gazete scraping başladı - Tarih: {target_date}')
        
        try:
            content = self.scrape_resmi_gazete(target_date)
            if content:
                if options['output']:
                    self.save_to_file(content, options['output'])
                self.stdout.write(
                    self.style.SUCCESS(f'Scraping tamamlandı. İçerik uzunluğu: {len(content)} karakter')
                )
                return content
            else:
                self.stdout.write(
                    self.style.WARNING('İçerik bulunamadı')
                )
        except Exception as e:
            logger.error(f"Resmi Gazete scraping hatası: {e}")
            self.stdout.write(
                self.style.ERROR(f'Hata: {e}')
            )

    def scrape_resmi_gazete(self, target_date):
        """Resmi Gazete içeriklerini scrape eder"""
        
        # Resmi Gazete URL formatı
        date_str = target_date.strftime('%d.%m.%Y')
        base_url = "https://www.resmigazete.gov.tr"
        
        # Ana sayfa üzerinden günlük gazete linkini bul
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            # Ana sayfa
            response = requests.get(base_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Günlük gazete bul
            gazette_link = None
            
            # Çeşitli CSS seçiciler dene
            possible_selectors = [
                'a[href*="eskiler"]',
                'a[href*="gunluk"]',
                '.gazete-link',
                'a[title*="Gazete"]',
                f'a[href*="{target_date.strftime("%Y")}"]'
            ]
            
            for selector in possible_selectors:
                links = soup.select(selector)
                for link in links:
                    if target_date.strftime('%d/%m/%Y') in link.get_text() or \
                       target_date.strftime('%d.%m.%Y') in link.get_text():
                        gazette_link = link.get('href')
                        break
                if gazette_link:
                    break
            
            if not gazette_link:
                # Doğrudan URL dene
                gazette_url = f"{base_url}/eskiler/{target_date.strftime('%Y')}/{target_date.strftime('%m')}/{target_date.strftime('%Y%m%d')}.htm"
            else:
                gazette_url = base_url + gazette_link if gazette_link.startswith('/') else gazette_link
            
            self.stdout.write(f'Gazete URL: {gazette_url}')
            
            # Gazete içeriğini al
            response = requests.get(gazette_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            return self.parse_gazette_content(response.content, target_date)
            
        except requests.RequestException as e:
            logger.error(f"HTTP isteği hatası: {e}")
            return None
        except Exception as e:
            logger.error(f"Beklenmeyen hata: {e}")
            return None

    def parse_gazette_content(self, html_content, target_date):
        """HTML içeriğini parse eder ve yapılandırılmış metin döndürür"""
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Ana içerik container'ını bul
        content_div = soup.find('div', class_='content') or \
                     soup.find('div', class_='main-content') or \
                     soup.find('div', id='content') or \
                     soup.find('body')
        
        if not content_div:
            return None
        
        # Script ve style taglerini temizle
        for script in content_div(["script", "style"]):
            script.decompose()
        
        # Başlıkları ve içerikleri çıkar
        content = {
            'date': target_date.strftime('%d.%m.%Y'),
            'sections': [],
            'full_text': ''
        }
        
        # Bölüm başlıklarını bul
        section_headers = content_div.find_all(['h1', 'h2', 'h3', 'strong', 'b'])
        
        current_section = None
        
        for element in content_div.descendants:
            if element.name in ['h1', 'h2', 'h3', 'strong', 'b']:
                text = element.get_text().strip()
                if len(text) > 10 and any(keyword in text.upper() for keyword in 
                    ['YÜRÜTME', 'İDARE', 'YARGI', 'YÖNETMELİK', 'TEBLİĞ', 'KURUL', 'İLÂN']):
                    current_section = {
                        'title': text,
                        'content': ''
                    }
                    content['sections'].append(current_section)
            
            elif element.name == 'p' and current_section:
                text = element.get_text().strip()
                if text:
                    current_section['content'] += text + '\n\n'
        
        # Tam metni oluştur
        content['full_text'] = content_div.get_text()
        
        # Metni temizle
        content['full_text'] = re.sub(r'\s+', ' ', content['full_text']).strip()
        
        return content

    def save_to_file(self, content, filepath):
        """İçeriği dosyaya kaydet"""
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"Resmi Gazete - {content['date']}\n")
                f.write("=" * 50 + "\n\n")
                
                for section in content['sections']:
                    f.write(f"{section['title']}\n")
                    f.write("-" * len(section['title']) + "\n")
                    f.write(f"{section['content']}\n\n")
        except Exception as e:
            logger.error(f"Dosya kaydetme hatası: {e}")