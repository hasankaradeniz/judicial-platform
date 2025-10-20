# faiss_query/mevzuat_integration.py

import re
import requests
from bs4 import BeautifulSoup
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

def extract_law_numbers(text):
    """Metinden kanun numaralarını çıkar"""
    patterns = [
        r'(\d{3,5})\s*sayılı',  # 6306 sayılı
        r'(\d{3,5})\s*no\.?lu',  # 6306 nolu  
        r'(\d{3,5})\s*numaralı',  # 6306 numaralı
        r'(\d{3,5})\s*sayılı\s*kanun',  # 6306 sayılı kanun
        r'kanun\s*no\.?\s*(\d{3,5})',  # kanun no 6306
        r'(\d{3,5})\s*sk',  # 6306 sk
        r'(\d{3,5})\s*s\.k',  # 6306 s.k
    ]
    
    law_numbers = set()
    text_lower = text.lower()
    
    for pattern in patterns:
        matches = re.finditer(pattern, text_lower)
        for match in matches:
            number = match.group(1)
            if number.isdigit() and 100 <= int(number) <= 9999:  # Geçerli kanun numarası aralığı
                law_numbers.add(number)
    
    return sorted(list(law_numbers))  # Sıralı liste döndür

def get_updated_law_info(law_numbers, max_laws=3):
    """Kanun bilgilerini al - önce cache'den, sonra temel bilgilerle"""
    law_info = {}
    
    # Yaygın kanunların temel bilgileri
    known_laws = {
        '6306': {
            'title': '6306 sayılı Afet Riski Altındaki Alanların Dönüştürülmesi Hakkında Kanun',
            'content_preview': 'Afet riski altındaki alanlar ile bu alanlar dışındaki riskli yapıların bulunduğu arsa ve arazilerde, iyileştirme, tahliye ve yenileme yoluyla dönüştürme işlemlerinin usul ve esasları düzenlenmiştir.',
            'last_update': 'Son değişiklik: 2023 yılı',
            'note': 'Yeter çoğunluk konusunda son düzenlemeler dikkate alınmalıdır.'
        },
        '4857': {
            'title': '4857 sayılı İş Kanunu',
            'content_preview': 'İş ilişkilerini düzenleyen temel kanundur. İş sözleşmesinin kurulması, işleyişi ve sona ermesi ile ilgili hükümler içerir.',
            'last_update': 'Çeşitli tarihlerde değişiklikler yapılmıştır'
        },
        '818': {
            'title': '818 sayılı Borçlar Kanunu (Mülga)',  
            'content_preview': 'Bu kanun mülga olmuş, yerine 6098 sayılı Türk Borçlar Kanunu yürürlüğe girmiştir.',
            'last_update': '2012 yılında yürürlükten kaldırılmıştır'
        },
        '6098': {
            'title': '6098 sayılı Türk Borçlar Kanunu',
            'content_preview': 'Borç ilişkilerini düzenleyen temel kanundur. Sözleşme hukuku, haksız fiil, sebepsiz zenginleşme gibi konuları kapsar.',
            'last_update': '2011 yılında yürürlüğe girmiştir'
        },
        '5237': {
            'title': '5237 sayılı Türk Ceza Kanunu',
            'content_preview': 'Suçlar ve cezaları düzenleyen temel kanundur.',
            'last_update': 'Çeşitli tarihlerde güncellemeler yapılmıştır'
        }
    }
    
    for law_number in law_numbers[:max_laws]:
        cache_key = f'mevzuat_law_{law_number}'
        
        try:
            cached_info = cache.get(cache_key)
            if cached_info:
                law_info[law_number] = cached_info
                continue
        except:
            pass  # Cache hatası varsa devam et
        
        # Bilinen kanunlardan kontrol et
        if law_number in known_laws:
            law_data = known_laws[law_number].copy()
            law_data['law_number'] = law_number
            law_data['url'] = f"https://www.mevzuat.gov.tr/MevzuatMetin/{law_number}"
            
            # Cache'e kaydet (24 saat)
            try:
                cache.set(cache_key, law_data, 86400)
            except:
                pass
                
            law_info[law_number] = law_data
            logger.info(f"Kanun {law_number} bilgisi yerel veri tabanından alındı")
        else:
            # Bilinmeyen kanunlar için temel bilgi
            law_data = {
                'title': f"{law_number} sayılı Kanun",
                'content_preview': f"Bu kanunun güncel metni için mevzuat.gov.tr'yi ziyaret ediniz.",
                'last_update': "Güncel bilgi mevzuat.gov.tr'de bulunabilir",
                'url': f"https://www.mevzuat.gov.tr/MevzuatMetin/{law_number}",
                'law_number': law_number,
                'note': 'Güncel değişiklikler dikkate alınmalıdır.'
            }
            
            law_info[law_number] = law_data
            logger.info(f"Kanun {law_number} için temel bilgi oluşturuldu")
    
    return law_info

def create_enhanced_prompt(olay, law_info):
    """Kanun bilgileri ile zenginleştirilmiş prompt oluştur"""
    base_prompt = f"""Aşağıdaki olaya göre Türk hukukuna göre genel bir hukuki açıklama yap. Açıklama sade, net ve bilgi verici olsun.

Olay: {olay}"""
    
    if law_info:
        base_prompt += "\n\nGÜNCEL MEVZUAT BİLGİLERİ:"
        for law_number, info in law_info.items():
            base_prompt += f"""
            
{law_number} sayılı Kanun - {info['title']}
Son Güncelleme: {info['last_update']}
İçerik: {info['content_preview']}"""
        
        base_prompt += "\n\nLütfen yukarıdaki güncel mevzuat bilgilerini dikkate alarak hukuki değerlendirme yap. Eskimiş bilgi vermemeye özen göster."
    
    return base_prompt

def test_law_extraction():
    """Test fonksiyonu - kanun numarası çıkarma"""
    test_texts = [
        "6306 sayılı kanunda yeter çoğunluk",
        "4857 nolu iş kanunu",
        "5237 numaralı TCK",
        "818 sayılı Borçlar Kanunu"
    ]
    
    for text in test_texts:
        numbers = extract_law_numbers(text)
        print(f"Metin: {text}")
        print(f"Çıkarılan kanun numaraları: {numbers}")
        print("---")

if __name__ == "__main__":
    test_law_extraction()