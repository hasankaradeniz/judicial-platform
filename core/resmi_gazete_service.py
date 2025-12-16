import google.generativeai as genai
from django.conf import settings
import logging
from datetime import datetime, timedelta
import json
import re
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class ResmiGazeteService:
    """Resmi Gazete içeriklerini AI ile özetleyen servis"""
    
    def __init__(self):
        # Gemini API key'i settings'den al
        self.api_key = getattr(settings, 'GEMINI_API_KEY', None)
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-2.5-flash')
        else:
            logger.warning("GEMINI_API_KEY bulunamadı")
            self.model = None

    def create_daily_summary(self, gazette_content: Dict) -> Dict:
        """Günlük resmi gazete için detaylı özet oluşturur"""
        
        if not self.model:
            logger.error("Gemini model bulunamadı")
            return None
        
        try:
            # İlk olarak yapılandırılmış özet oluştur
            structured_summary = self.create_structured_summary_from_sections(gazette_content)
            
            # AI ile zenginleştir (optimize edilmiş - sadece ilk 5 öğe)
            logger.info("AI ile içerik zenginleştiriliyor (optimize edilmiş)...")
            enhanced_summary = self.enhance_with_ai(gazette_content, structured_summary)
            
            return enhanced_summary
            
            # Prompt template - De Jure AI formatında
            prompt = f"""
Sen uzman bir hukuk editörüsün. Aşağıdaki {gazette_content['date']} tarihli Resmi Gazete içeriğini analiz et ve De Jure AI formatında profesyonel bir özet hazırla.

MEVCUT VERİ ({gazette_content.get('item_count', 0)} öğe):
{gazette_content['full_text'][:8000]}

GÖREV:
ÖNEMLİ: "Türk Devleti" ifadesi kullanma. "Türkiye Cumhuriyeti" veya spesifik kurum adını kullan.
Her önemli düzenleme için şu formatta özet yaz:

–– [Düzenleme Başlığı]

[Hangi kurum/bakanlık tarafından yayımlandığı, temel amacı, hangi alanı etkilediği ve önemli hükümlerini 2-3 cümle ile açıkla.]

BÖLÜMLER:
1. YÜRÜTME VE İDARE BÖLÜMÜ
   - YÖNETMELİKLER  
   - TEBLİĞLER
   - KURUL KARARLARI

2. YARGI BÖLÜMÜ
   - SAYIŞTAY KARARLARI

3. İLÂN BÖLÜMÜ

SADECE ÖNEMLİ/ETKİLİ OLAN DÜZENLEMELERİ ÖZETLe. Rutin atama kararları ve basit ilanlarla uğraşma.
"""

            # AI'dan özet al
            response = self.model.generate_content(prompt)
            summary_text = response.text
            
            # Özetli parse et ve yapılandır
            structured_summary = self.parse_ai_summary(summary_text, gazette_content['date'])
            
            return structured_summary
            
        except Exception as e:
            logger.error(f"AI özet oluşturma hatası: {e}")
            return None

    def parse_ai_summary(self, summary_text: str, date: str) -> Dict:
        """AI'dan gelen özeti yapılandırır"""
        
        summary = {
            'date': date,
            'header': f"Resmî Gazete\n\n{date}",
            'sections': [],
            'raw_summary': summary_text
        }
        
        # Bölümleri ayır
        sections_map = {
            'YÜRÜTME VE İDARE BÖLÜMÜ': [],
            'YARGI BÖLÜMÜ': [],
            'İLÂN BÖLÜMÜ': []
        }
        
        current_main_section = None
        current_sub_section = None
        current_items = []
        
        lines = summary_text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Ana bölüm başlığı
            if 'YÜRÜTME VE İDARE' in line.upper():
                current_main_section = 'YÜRÜTME VE İDARE BÖLÜMÜ'
                current_sub_section = None
                current_items = []
            elif 'YARGI' in line.upper():
                current_main_section = 'YARGI BÖLÜMÜ'
                current_sub_section = None
                current_items = []
            elif 'İLÂN' in line.upper():
                current_main_section = 'İLÂN BÖLÜMÜ'
                current_sub_section = None
                current_items = []
            
            # Alt bölüm başlığı
            elif line.upper() in ['YÖNETMELİKLER', 'TEBLİĞLER', 'KURUL KARARLARI', 'SAYIŞTAY KARARLARI']:
                if current_sub_section and current_items:
                    sections_map[current_main_section].append({
                        'title': current_sub_section,
                        'items': current_items.copy()
                    })
                current_sub_section = line.upper()
                current_items = []
            
            # Düzenleme başlığı (–– ile başlayanlar)
            elif line.startswith('––'):
                title = line.replace('––', '').strip()
                current_items.append({
                    'title': title,
                    'content': ''
                })
            
            # Düzenleme içeriği
            elif current_items and line:
                current_items[-1]['content'] += line + ' '
        
        # Son bölümü ekle
        if current_sub_section and current_items:
            sections_map[current_main_section].append({
                'title': current_sub_section,
                'items': current_items.copy()
            })
        
        # Yapılandırılmış formata çevir
        for main_section, sub_sections in sections_map.items():
            if sub_sections:
                summary['sections'].append({
                    'title': main_section,
                    'subsections': sub_sections
                })
        
        return summary

    def generate_email_content(self, summary: Dict) -> Dict:
        """Email için HTML içerik oluşturur"""
        
        if not summary:
            return None
        
        # Email başlığı - yeni format
        subject = f"GÜNLÜK RESMİ GAZETE BÜLTENİ - {summary['date']} TARİHLİ RESMİ GAZETE İÇERİKLERİ"
        
        # HTML template
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{subject}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f8f9fa;
        }}
        .header {{
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            padding: 30px;
            text-align: center;
            border-radius: 10px 10px 0 0;
            margin-bottom: 0;
        }}
        .logo {{
            background: white;
            padding: 15px;
            border-radius: 8px;
            display: inline-block;
            margin-bottom: 15px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .logo img {{
            height: 80px;
            width: auto;
            max-width: 250px;
        }}
        .logo-text {{
            color: #2a5298;
            font-size: 24px;
            font-weight: 700;
            letter-spacing: 1px;
            margin: 0;
        }}
        .header h1 {{
            margin: 0;
            font-size: 24px;
            font-weight: 600;
        }}
        .ai-badge {{
            background: rgba(255,255,255,0.2);
            padding: 5px 12px;
            border-radius: 15px;
            font-size: 12px;
            margin-top: 8px;
            display: inline-block;
        }}
        .content {{
            background: white;
            padding: 30px;
            border-radius: 0 0 10px 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .section {{
            margin-bottom: 40px;
        }}
        .section-title {{
            color: #1e3c72;
            font-size: 18px;
            font-weight: 700;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e9ecef;
        }}
        .subsection {{
            margin-bottom: 25px;
        }}
        .subsection-title {{
            color: #495057;
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 15px;
        }}
        .regulation {{
            margin-bottom: 20px;
            padding: 15px;
            background: #f8f9fa;
            border-left: 4px solid #2a5298;
            border-radius: 5px;
            transition: all 0.3s ease;
        }}
        .regulation:hover {{
            background: #e9ecef;
            cursor: pointer;
        }}
        .regulation-title {{
            font-weight: 600;
            color: #1e3c72;
            margin-bottom: 8px;
            text-decoration: none;
        }}
        .regulation-title a {{
            color: #1e3c72;
            text-decoration: none;
        }}
        .regulation-title a:hover {{
            color: #2a5298;
            text-decoration: underline;
        }}
        .link-icon {{
            color: #2a5298;
            font-size: 12px;
            margin-left: 5px;
        }}
        .regulation-content {{
            color: #495057;
            line-height: 1.7;
        }}
        .footer {{
            background: linear-gradient(135deg, #2a5298 0%, #1e3c72 100%);
            color: white;
            text-align: center;
            padding: 30px 20px;
            font-size: 12px;
            margin-top: 30px;
            border-radius: 0 0 10px 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .brand {{
            color: white;
            font-weight: 600;
        }}
        .footer a {{
            color: rgba(255,255,255,0.9) !important;
            text-decoration: none;
        }}
        .footer a:hover {{
            color: white !important;
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">
            <img src="https://www.lexatech.ai/static/core/images/logo.jpeg" alt="LexaTech AI" onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
            <div class="logo-text" style="display: none;">LexaTech AI</div>
        </div>
        <h1>Resmî Gazete</h1>
        <p style="margin: 10px 0 0 0; opacity: 0.9; font-size: 16px;">{summary['date']}</p>
        <div class="ai-badge">🤖 AI Destekli Analiz</div>
    </div>
    
    <div class="content">
"""
        
        # Bölümleri ekle
        for section in summary.get('sections', []):
            html_content += f"""
        <div class="section">
            <h2 class="section-title">{section['title']}</h2>
"""
            
            for subsection in section.get('subsections', []):
                html_content += f"""
            <div class="subsection">
                <h3 class="subsection-title">{subsection['title']}</h3>
"""
                
                for item in subsection.get('items', []):
                    item_link = item.get('link', 'https://www.resmigazete.gov.tr/')
                    html_content += f"""
                <div class="regulation">
                    <div class="regulation-title">
                        <a href="{item_link}" target="_blank">–– {item['title']}</a>
                        <span class="link-icon">🔗</span>
                    </div>
                    <div class="regulation-content">{item['content'].strip()}</div>
                </div>
"""
                
                html_content += "            </div>\n"
            
            html_content += "        </div>\n"
        
        # Footer
        html_content += f"""
    </div>
    
    <div class="footer">
        <p style="margin-bottom: 10px; font-size: 14px; font-weight: 600;">
            <a href="https://www.lexatech.ai" style="color: rgba(255,255,255,0.9); text-decoration: none;">
                www.lexatech.ai
            </a>
        </p>
        
        <p style="margin-bottom: 10px; font-size: 13px; color: rgba(255,255,255,0.8);">
            <a href="tel:02129700644" style="color: rgba(255,255,255,0.9); text-decoration: none;">0 212 970 06 44</a> - 
            <a href="mailto:lexatech.ai@gmail.com" style="color: rgba(255,255,255,0.9); text-decoration: none;">lexatech.ai@gmail.com</a>
        </p>
        
        <p style="margin-bottom: 8px; font-size: 12px; color: rgba(255,255,255,0.7);">
            &nbsp;
        </p>
        
        <p style="margin-bottom: 8px; font-size: 12px; color: rgba(255,255,255,0.8);">
            Yeşilköy Mahallesi Atatürk Caddesi, EGS Blokları No:12/1
        </p>
        
        <p style="margin-bottom: 15px; font-size: 12px; color: rgba(255,255,255,0.8);">
            Bakırköy/İstanbul
        </p>
        
        <p style="margin-bottom: 8px; font-size: 12px; color: rgba(255,255,255,0.7);">
            &nbsp;
        </p>
        
        <p style="margin-bottom: 8px; font-size: 12px; color: rgba(255,255,255,0.7);">
            &nbsp;
        </p>
        
        <p style="margin-bottom: 15px; font-size: 11px; color: rgba(255,255,255,0.7);">
            <a href="mailto:lexatech.ai@gmail.com?subject=Mail Aboneliği İptali" style="color: rgba(255,255,255,0.8); text-decoration: none;">
                LexaTech AI'dan mail almak istemiyorsanız buraya tıklayarak mail aboneliğinizi güncelleyebilirsiniz.
            </a>
        </p>
        
        <p style="font-size: 11px; color: rgba(255,255,255,0.6); margin: 0;">
            © 2025 LexaTech AI
        </p>
    </div>
</body>
</html>
"""
        
        return {
            'subject': subject,
            'html_content': html_content,
            'plain_text': self.generate_plain_text(summary)
        }

    def generate_plain_text(self, summary: Dict) -> str:
        """Plain text email içeriği oluşturur"""
        
        content = f"Resmî Gazete - {summary['date']}\n"
        content += "=" * 50 + "\n\n"
        
        for section in summary.get('sections', []):
            content += f"{section['title']}\n\n"
            
            for subsection in section.get('subsections', []):
                content += f"{subsection['title']}\n\n"
                
                for item in subsection.get('items', []):
                    content += f"–– {item['title']}\n\n"
                    content += f"{item['content'].strip()}\n\n"
                
                content += "\n"
            
            content += "\n"
        
        content += "\nLexaTech AI tarafından otomatik olarak oluşturulmuştur.\n"
        content += "Bu email AI destekli içerik analizi ile hazırlanmıştır.\n"
        
        return content

    def create_structured_summary_from_sections(self, gazette_content: Dict) -> Dict:
        """AI olmadan direkt yapılandırılmış özet oluşturur"""
        
        try:
            summary = {
                'date': gazette_content.get('date', ''),
                'header': f"Resmî Gazete\n\n{gazette_content.get('date', '')}",
                'sections': [],
                'raw_summary': f"Bugünkü Resmi Gazete'de {gazette_content.get('item_count', 0)} öğe bulunmaktadır."
            }
            
            # Sections verisini dönüştür
            sections_data = gazette_content.get('sections', {})
            
            # Ana PDF linkini en başa ekle
            main_pdf = None
            regular_items = []
            
            for section_name, items in sections_data.items():
                for item in items:
                    if 'resmi gazete' in item.get('title', '').lower() and 'sayı' in item.get('title', '').lower():
                        main_pdf = item
                    else:
                        regular_items.append((section_name, item))
            
            # Ana PDF varsa en başa ekle
            if main_pdf:
                summary['sections'].insert(0, {
                    'title': 'GÜNLÜK RESMİ GAZETE',
                    'subsections': [{
                        'title': 'TAM İÇERİK',
                        'items': [{
                            'title': main_pdf['title'],
                            'content': main_pdf['content'],
                            'link': main_pdf.get('link', 'https://www.resmigazete.gov.tr/')
                        }]
                    }]
                })
            
            # Bölümler oluştur
            yönetmelikler = []
            tebligler = []
            kurul_kararlari = []
            ilan_tebliger = []
            
            for section_name, item in regular_items:
                title = item.get('title', '').lower()
                content = item.get('content', '').lower()
                
                # Daha akıllı kategorileme - title ve content'e bak
                combined_text = f"{title} {content}"
                
                # Sadece gerçek ilanları İLÂN bölümüne koy
                is_real_announcement = any(term in combined_text for term in [
                    'ilan', 'ihale', 'artırma', 'eksiltme', 'başvuru', 
                    'duyuru', 'kayıp belge', 'konkordato'
                ])
                
                # YÜRÜTME VE İDARE kategorisindeki öğeleri belirle
                is_administrative = any(term in combined_text for term in [
                    'yönetmelik', 'tebliğ', 'kurul', 'karar', 'bakanlar kurulu',
                    'cumhurbaşkanı kararı', 'genelge', 'tamim', 'yönerge', 'üniversite'
                ])
                
                # Öncelik: Administrative işlemler YÜRÜTME VE İDARE'ye
                if is_administrative or section_name == 'YÜRÜTME VE İDARE BÖLÜMÜ':
                    if 'yönetmelik' in combined_text:
                        yönetmelikler.append(item)
                    elif 'tebliğ' in combined_text and 'yönetmelik' not in combined_text:
                        tebligler.append(item)
                    elif any(term in combined_text for term in ['kurul', 'karar', 'cumhurbaşkanı']):
                        kurul_kararlari.append(item)
                    else:
                        # Diğer idari işlemler yönetmelikler kategorisine
                        yönetmelikler.append(item)
                elif is_real_announcement:
                    # Sadece gerçek ilanlar buraya
                    ilan_tebliger.append(item)
                else:
                    # Bilinmeyen kategoriler YÜRÜTME VE İDARE'ye
                    yönetmelikler.append(item)
            
            # YÜRÜTME VE İDARE BÖLÜMÜ
            if yönetmelikler or tebligler or kurul_kararlari:
                yönetim_subsections = []
                
                if yönetmelikler:
                    yönetim_subsections.append({
                        'title': 'YÖNETMELİKLER',
                        'items': [
                            {
                                'title': item['title'],
                                'content': item['content'],
                                'link': item.get('link', 'https://www.resmigazete.gov.tr/')
                            } for item in yönetmelikler
                        ]
                    })
                
                if tebligler:
                    yönetim_subsections.append({
                        'title': 'TEBLİĞLER',
                        'items': [
                            {
                                'title': item['title'],
                                'content': item['content'],
                                'link': item.get('link', 'https://www.resmigazete.gov.tr/')
                            } for item in tebligler
                        ]
                    })
                
                if kurul_kararlari:
                    yönetim_subsections.append({
                        'title': 'KURUL KARARLARI',
                        'items': [
                            {
                                'title': item['title'],
                                'content': item['content'],
                                'link': item.get('link', 'https://www.resmigazete.gov.tr/')
                            } for item in kurul_kararlari
                        ]
                    })
                
                summary['sections'].append({
                    'title': 'YÜRÜTME VE İDARE BÖLÜMÜ',
                    'subsections': yönetim_subsections
                })
            
            # İLÂN BÖLÜMÜ - Sadece standart kategoriler (gerçek ilanlar varsa onları da ekle)
            ilan_items = [
                {
                    'title': 'a - Yargı İlanları',
                    'content': 'Yargı organlarınca verilen çeşitli kararlar ve ilanlar',
                    'link': 'https://www.resmigazete.gov.tr/'
                },
                {
                    'title': 'b - Artırma, Eksiltme ve İhale İlânları',
                    'content': 'Kamu kurum ve kuruluşlarının ihale ve artırma ilanları',
                    'link': 'https://www.resmigazete.gov.tr/'
                },
                {
                    'title': 'c - Çeşitli İlânlar',
                    'content': 'Kayıp belgeler, ticaret sicili ilanları ve diğer çeşitli ilanlar',
                    'link': 'https://www.resmigazete.gov.tr/'
                },
                {
                    'title': '– T.C. Merkez Bankasınca Belirlenen Devlet İç Borçlanma Senetlerinin Günlük Değerleri',
                    'content': 'Devlet İç Borçlanma Senetlerinin günlük değerleri ve döviz kurları',
                    'link': 'https://www.resmigazete.gov.tr/'
                }
            ]
            
            # Gerçek ilanları ekle (eğer varsa)
            if ilan_tebliger:
                for item in ilan_tebliger:
                    ilan_items.append({
                        'title': item['title'],
                        'content': item['content'],
                        'link': item.get('link', 'https://www.resmigazete.gov.tr/')
                    })
            
            ilan_subsections = [{
                'title': 'TEBLİĞLER',
                'items': ilan_items
            }]
            
            summary['sections'].append({
                'title': 'İLÂN BÖLÜMÜ',
                'subsections': ilan_subsections
            })
            
            return summary
            
        except Exception as e:
            logger.error(f"Yapılandırılmış özet hatası: {e}")
            return {
                'date': gazette_content.get('date', ''),
                'header': f"Resmî Gazete\n\n{gazette_content.get('date', '')}",
                'sections': [],
                'raw_summary': "Günlük resmi gazete içeriği mevcut."
            }

    def enhance_with_ai(self, gazette_content: Dict, fallback_summary: Dict) -> Dict:
        """AI ile fallback summary'yi zenginleştirir"""
        
        try:
            if not self.model or not fallback_summary.get('sections'):
                logger.warning("AI model yok veya bölümler boş - fallback kullanılıyor")
                return fallback_summary
            
            enhanced_sections = []
            total_items = 0
            processed_items = 0
            
            # Önce toplam item sayısını hesapla
            for section in fallback_summary['sections']:
                for subsection in section.get('subsections', []):
                    total_items += len(subsection.get('items', []))
            
            logger.info(f"AI ile zenginleştirme başlatılıyor: {total_items} öğe")
            
            # İlk 10 öğe için AI kullan (optimize)
            max_ai_items = 10
            
            for section in fallback_summary['sections']:
                enhanced_section = {
                    'title': section['title'],
                    'subsections': []
                }
                
                for subsection in section.get('subsections', []):
                    enhanced_subsection = {
                        'title': subsection['title'],
                        'items': []
                    }
                    
                    # Her öğe için AI ile detaylı açıklama oluştur (limit ile)
                    for item in subsection.get('items', []):
                        if processed_items < max_ai_items:
                            enhanced_item = self.create_ai_description(item)
                            processed_items += 1
                            logger.info(f"AI işlendi: {processed_items}/{max_ai_items}")
                        else:
                            # Limit aşıldı, orijinal içeriği temizle ve kullan
                            enhanced_item = self.clean_fallback_content(item)
                        
                        enhanced_subsection['items'].append(enhanced_item)
                    
                    enhanced_section['subsections'].append(enhanced_subsection)
                
                enhanced_sections.append(enhanced_section)
            
            # Enhanced summary oluştur
            enhanced_summary = fallback_summary.copy()
            enhanced_summary['sections'] = enhanced_sections
            
            logger.info(f"AI enhancement tamamlandı: {processed_items} öğe AI ile işlendi")
            return enhanced_summary
            
        except Exception as e:
            logger.error(f"AI enhancement hatası: {e}")
            return fallback_summary

    def create_ai_description(self, item: Dict) -> Dict:
        """Tek bir öğe için AI ile detaylı açıklama oluşturur"""
        
        try:
            title = item.get('title', '')
            content = item.get('content', '')
            
            # Çok uzunsa kısalt
            if len(title) > 200:
                title = title[:200] + "..."
            if len(content) > 500:
                content = content[:500] + "..."
            
            # AI prompt - çok kısa ve hızlı
            prompt = f"""1-2 cümle açıklama:
{title}
Hangi kurum tarafından, hangi amaçla? "Türk Devleti" ifadesi kullanma, "Türkiye Cumhuriyeti" veya kurum adını kullan. Max 150 karakter."""
            
            # AI'dan açıklama al (timeout ile)
            import time
            start_time = time.time()
            
            response = self.model.generate_content(prompt)
            ai_description = response.text.strip()
            
            elapsed = time.time() - start_time
            logger.debug(f"AI response time: {elapsed:.2f}s")
            
            # AI response'u temizle
            ai_description = ai_description.replace('İdari İşlem:', '').strip()
            ai_description = ai_description.replace('İdari İşlem', '').strip()
            
            # Başlangıçtaki gereksiz karakterleri temizle
            if ai_description.startswith('- '):
                ai_description = ai_description[2:].strip()
            
            # Temizle ve kısalt
            if len(ai_description) > 300:
                ai_description = ai_description[:300] + "..."
            
            # Boşsa fallback (temizlenmiş content)
            if not ai_description or len(ai_description) < 20:
                clean_content = content.replace('İdari İşlem:', '').replace('İdari İşlem', '').strip()
                if clean_content.startswith('- '):
                    clean_content = clean_content[2:].strip()
                ai_description = clean_content[:200] + "..." if len(clean_content) > 200 else clean_content
            
            return {
                'title': title,
                'content': ai_description,
                'link': item.get('link', 'https://www.resmigazete.gov.tr/')
            }
            
        except Exception as e:
            logger.error(f"AI açıklama oluşturma hatası: {e}")
            # Hata durumunda orijinal içeriği temizle ve kısalt
            fallback_content = item.get('content', '')
            
            # "İdari İşlem:" gibi prefix'leri temizle
            fallback_content = fallback_content.replace('İdari İşlem:', '').strip()
            fallback_content = fallback_content.replace('İdari İşlem', '').strip()
            
            # Başlangıçtaki "- " karakterlerini temizle
            if fallback_content.startswith('- '):
                fallback_content = fallback_content[2:].strip()
            
            # Çok kısaysa başlıktan yardım al
            if len(fallback_content) < 50:
                title = item.get('title', '')
                fallback_content = f"Bu düzenleme {title.lower()} ile ilgili yeni bir düzenlemedir."
            
            if len(fallback_content) > 200:
                fallback_content = fallback_content[:200] + "..."
            
            return {
                'title': item.get('title', ''),
                'content': fallback_content,
                'link': item.get('link', 'https://www.resmigazete.gov.tr/')
            }

    def clean_fallback_content(self, item: Dict) -> Dict:
        """AI işlemi olmayan içerikler için temiz fallback oluştur"""
        
        title = item.get('title', '')
        content = item.get('content', '')
        
        # "İdari İşlem:" gibi prefix'leri temizle
        clean_content = content.replace('İdari İşlem:', '').strip()
        clean_content = clean_content.replace('İdari İşlem', '').strip()
        clean_content = clean_content.replace(f'{title} - İdari İşlem', '').strip()
        
        # Başlangıçtaki "- " karakterlerini temizle
        if clean_content.startswith('- '):
            clean_content = clean_content[2:].strip()
        
        # Çok kısaysa veya temizlendikten sonra boşsa başlıktan yardım al
        if len(clean_content) < 30:
            # Başlıktan kategorileri çıkar
            if 'yönetmelik' in title.lower():
                clean_content = f"Bu yönetmelik ile ilgili yeni bir düzenleme yapılmıştır."
            elif 'tebliğ' in title.lower():
                clean_content = f"Bu tebliğ ile ilgili güncelleme yapılmıştır."
            elif 'üniversite' in title.lower():
                clean_content = f"Üniversite yönetmeliği ile ilgili düzenleme."
            else:
                clean_content = f"Bu düzenleme ile ilgili yeni bir güncelleme yapılmıştır."
        
        if len(clean_content) > 200:
            clean_content = clean_content[:200] + "..."
        
        return {
            'title': title,
            'content': clean_content,
            'link': item.get('link', 'https://www.resmigazete.gov.tr/')
        }