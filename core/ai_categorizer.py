"""
AI Kategorilendirme Servisi
"""
import os
import logging
from typing import Tuple
import google.generativeai as genai
from django.conf import settings

logger = logging.getLogger(__name__)

class AICategorizer:
    def __init__(self):
        api_key = getattr(settings, "GEMINI_API_KEY", os.getenv("GEMINI_API_KEY"))
        if api_key:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel("gemini-1.5-flash")
            self.available = True
        else:
            self.available = False
    
    def categorize_content(self, title: str, scraped_category: str = "") -> Tuple[str, str]:
        if self.available:
            ai_result = self._ai_categorize(title, scraped_category)
            if ai_result:
                return ai_result
        
        return self._rule_based_categorize(title, scraped_category)
    
    def _ai_categorize(self, title: str, scraped_category: str) -> Tuple[str, str] or None:
        try:
            prompt = f"""Resmi Gazete içerik kategorisi:

BAŞLIK: {title}

Bu içeriği kategorilendirin:

CONTENT_TYPE seçenekleri: yurutme_idare, anayasa_mahkemesi, yargitay, danistay, ilan
CATEGORY seçenekleri: cumhurbaskani_karari, atama_karari, yonetmelik, teblig, genelge, bakanlar_kurulu_karari, kurul_karari, ilan, gunluk_sayi, other

Format:
CONTENT_TYPE: [seçim]
CATEGORY: [seçim]"""

            response = self.model.generate_content(prompt)
            
            if response and response.text:
                return self._parse_ai_categorization(response.text)
                
        except Exception as e:
            logger.error(f"AI kategorilendirme hatası: {e}")
            
        return None
    
    def _parse_ai_categorization(self, response_text: str):
        try:
            lines = response_text.strip().split(n)
            content_type = None
            category = None
            
            for line in lines:
                line = line.strip()
                if line.startswith("CONTENT_TYPE:"):
                    content_type = line.split(":", 1)[1].strip()
                elif line.startswith("CATEGORY:"):
                    category = line.split(":", 1)[1].strip()
            
            if content_type and category:
                valid_content_types = ["yurutme_idare", "anayasa_mahkemesi", "yargitay", "danistay", "ilan"]
                valid_categories = ["cumhurbaskani_karari", "atama_karari", "yonetmelik", "teblig", "genelge", "bakanlar_kurulu_karari", "kurul_karari", "ilan", "gunluk_sayi", "other"]
                
                if content_type in valid_content_types and category in valid_categories:
                    return (content_type, category)
                    
        except Exception as e:
            logger.error(f"Parse hatası: {e}")
            
        return None
    
    def _rule_based_categorize(self, title: str, scraped_category: str) -> Tuple[str, str]:
        title_lower = title.lower()
        
        # Günlük sayı
        if "resmi gazete" in title_lower and "sayı" in title_lower:
            return ("yurutme_idare", "gunluk_sayi")
        
        # Yönetmelik
        if "yönetmelik" in title_lower:
            return ("yurutme_idare", "yonetmelik")
        
        # Tebliğ
        if "tebliğ" in title_lower or "teblig" in title_lower:
            return ("yurutme_idare", "teblig")
        
        # Cumhurbaşkanı kararları
        if any(word in title_lower for word in ["vekalet", "vekâlet"]):
            return ("yurutme_idare", "cumhurbaskani_karari")
        
        if any(word in title_lower for word in ["enerji", "elektrik", "transformatör"]):
            return ("yurutme_idare", "cumhurbaskani_karari")
        
        if "vergi" in title_lower:
            return ("yurutme_idare", "cumhurbaskani_karari")
        
        if "sahipsiz hayvan" in title_lower:
            return ("yurutme_idare", "cumhurbaskani_karari")
        
        # Atama
        if "atama" in title_lower:
            return ("yurutme_idare", "atama_karari")
        
        # Varsayılan
        return ("yurutme_idare", "other")

ai_categorizer = AICategorizer()
