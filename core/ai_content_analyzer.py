"""
AI Content Analyzer - İçerik analizi için yapay zeka servisi
"""
import os
import logging
from typing import Dict, Any, Optional
import google.generativeai as genai
from django.conf import settings

logger = logging.getLogger(__name__)

class AIContentAnalyzer:
    def __init__(self):
        api_key = getattr(settings, "GEMINI_API_KEY", os.getenv("GEMINI_API_KEY"))
        if api_key:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel("gemini-1.5-flash")
            self.available = True
        else:
            self.available = False
    
    def analyze_content(self, title: str, category: str) -> Dict[str, Any]:
        if not self.available:
            return self._get_fallback_analysis(title, category)
        
        try:
            prompt = f"""Türkiye Resmi Gazete düzenlemesi:
BAŞLIK: {title}
KATEGORİ: {category}

2-3 cümlelik açık özet yaz (max 150 kelime):"""
            
            response = self.model.generate_content(prompt)
            
            if response and response.text:
                return {"summary": response.text.strip(), "ai_generated": True}
            else:
                return self._get_fallback_analysis(title, category)
                
        except Exception as e:
            return self._get_fallback_analysis(title, category)
    
    def _get_fallback_analysis(self, title: str, category: str) -> Dict[str, Any]:
        title_lower = title.lower()
        
        if "enerji" in title_lower or "elektrik" in title_lower:
            summary = "Enerji sektörü ve altyapı yatırımlarına yönelik düzenleme yapılmıştır. Bu karar, enerji güvenliği ve sürdürülebilir kalkınma hedefleri doğrultusunda alınmış olup, sektördeki şirketler ve yatırımcılar için yeni fırsatlar yaratmaktadır."
        elif "vergi" in title_lower:
            summary = "Vergi mevzuatında önemli değişiklikler yapılmıştır. Bu düzenleme, mükellefler ve muhasebe meslek mensupları için yeni yükümlülükler getirirken, vergi adaleti ve tahsilat verimliliğinin artırılması hedeflenmektedir."
        elif "vekalet" in title_lower:
            summary = "Cumhurbaşkanlığına vekalet etme yetkisi düzenlenmiştir. Bu karar, devlet yönetiminin kesintisiz sürdürülmesi ve anayasal düzenin korunması açısından kritik önem taşımaktadır."
        elif "atama" in title_lower and "karar" in title_lower:
            summary = "Kamu kurum ve kuruluşlarında üst düzey personel atama işlemleri gerçekleştirilmiştir. Bu atamalar, kurumsal kapasite ve hizmet kalitesinin artırılması amacıyla yapılmıştır."
        elif "yönetmelik" in title_lower:
            summary = "İlgili konuda uygulama birliğini sağlayacak yönetmelik değişikliği yapılmıştır. Bu düzenleme, mevcut uygulamaları standardize ederek hizmet kalitesinin artırılmasını hedeflemektedir."
        elif "sahipsiz hayvan" in title_lower:
            summary = "Sahipsiz hayvanların korunması ve bakımına yönelik kurumsal yapılanma kararı alınmıştır. Bu düzenleme, hayvan refahı ve toplum sağlığı açısından önemli bir adım niteliğindedir."
        else:
            summary = "İdari İşlem kapsamında yapılan bu düzenleme, ilgili mevzuatın güncellenmesini ve uygulamada birliğin sağlanmasını amaçlamaktadır. Düzenleme, sektör paydaşları ve vatandaşlar için yeni haklar ve yükümlülükler getirmektedir."
        
        return {"summary": summary, "ai_generated": False}

ai_analyzer = AIContentAnalyzer()
