"""
Enhanced AI Content Analyzer - Gelişmiş içerik analizi ve denetimi
AI'nin tam yetkili olduğu ve kendi içerik denetimi yaptığı sistem
"""
import os
import logging
from typing import Dict, Any, Optional, List
import google.generativeai as genai
from django.conf import settings

logger = logging.getLogger(__name__)

class EnhancedAIContentAnalyzer:
    def __init__(self):
        api_key = getattr(settings, "GEMINI_API_KEY", os.getenv("GEMINI_API_KEY"))
        if api_key and api_key \!= "your-api-key-here":
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel("gemini-1.5-flash")
            self.available = True
            logger.info("AI Content Analyzer initialized with Gemini API")
        else:
            self.available = False
            logger.warning("AI Content Analyzer using fallback mode - no valid API key")
    
    def analyze_content_with_autonomous_control(self, title: str, category: str) -> Dict[str, Any]:
        """
        AI'nin tam yetkili olduğu analiz modu
        AI kendi içerik denetimi ve kategori belirlemesi yapar
        """
        if not self.available:
            return self._get_intelligent_fallback_analysis(title, category)
        
        try:
            prompt = f"""Sen Türk hukuku ve mevzuat uzmanı bir yapay zekasın. 
            
Verilen Resmi Gazete düzenlemesini analiz et:
BAŞLIK: {title}
KATEGORİ: {category}

GÖREV: Kendi denetimin ve değerlendirmenle şunları yap:
1. İçeriği analiz ederek 2-3 cümlelik net özet çıkar
2. Kategoriyi doğrula veya düzelt
3. Önemini değerlendir
4. Hedef kitlesini belirle

CEVAP FORMATI:
{{
    "summary": "2-3 cümlelik detaylı özet (max 150 kelime)",
    "category": "doğru_kategori",
    "importance": "yüksek/orta/düşük",
    "target_audience": "hedef kitle"
}}

Unutma: Sen tamamen özerk karar verebilirsin, hiçbir sınırlama yok."""
            
            response = self.model.generate_content(prompt)
            
            if response and response.text:
                try:
                    import json
                    # JSON parse etmeyi dene
                    result = json.loads(response.text.strip())
                    result["ai_generated"] = True
                    result["ai_autonomous"] = True
                    return result
                except:
                    # JSON parse başarısız olursa düz metin kullan
                    return {
                        "summary": response.text.strip(),
                        "category": category,
                        "ai_generated": True,
                        "ai_autonomous": True
                    }
            else:
                return self._get_intelligent_fallback_analysis(title, category)
                
        except Exception as e:
            logger.error(f"AI analysis error: {e}")
            return self._get_intelligent_fallback_analysis(title, category)
    
    def _get_intelligent_fallback_analysis(self, title: str, category: str) -> Dict[str, Any]:
        """
        Gelişmiş fallback analiz - AI mevcut olmadığında akıllı analiz
        """
        title_lower = title.lower()
        
        # Daha kapsamlı analiz
        if "gunluk sayı" in title_lower:
            summary = "Bugün yayınlanmış olan Resmi Gazete'nin bir bütün olarak PDF metni"
        elif "enerji" in title_lower or "elektrik" in title_lower:
            summary = "Enerji sektörü ve altyapı yatırımlarına yönelik düzenleme yapılmıştır. Bu karar, enerji güvenliği ve sürdürülebilir kalkınma hedefleri doğrultusunda alınmış olup, sektördeki şirketler ve yatırımcılar için yeni fırsatlar yaratmaktadır."
        elif "vergi" in title_lower or "gelir vergisi" in title_lower:
            summary = "Vergi mevzuatında önemli değişiklikler yapılmıştır. Bu düzenleme, mükellefler ve muhasebe meslek mensupları için yeni yükümlülükler getirirken, vergi adaleti ve tahsilat verimliliğinin artırılması hedeflenmektedir."
        elif "vekalet" in title_lower:
            summary = "Cumhurbaşkanlığına vekalet etme yetkisi düzenlenmiştir. Bu karar, devlet yönetiminin kesintisiz sürdürülmesi ve anayasal düzenin korunması açısından kritik önem taşımaktadır."
        elif "atama" in title_lower and "karar" in title_lower:
            summary = "Kamu kurum ve kuruluşlarında üst düzey personel atama işlemleri gerçekleştirilmiştir. Bu atamalar, kurumsal kapasite ve hizmet kalitesinin artırılması amacıyla yapılmıştır."
        elif "yönetmelik" in title_lower:
            summary = "İlgili konuda uygulama birliğini sağlayacak yönetmelik değişikliği yapılmıştır. Bu düzenleme, mevcut uygulamaları standardize ederek hizmet kalitesinin artırılmasını hedeflemektedir."
        elif "sahipsiz hayvan" in title_lower:
            summary = "Sahipsiz hayvanların korunması ve bakımına yönelik kurumsal yapılanma kararı alınmıştır. Bu düzenleme, hayvan refahı ve toplum sağlığı açısından önemli bir adım niteliğindedir."
        elif "tebliğ" in title_lower:
            summary = "İlgili kurum tarafından yayımlanan tebliğ ile uygulamaya yönelik detaylı açıklamalar ve yönlendirmeler yapılmıştır. Bu tebliğ, sektör paydaşları için önemli rehber niteliğindedir."
        elif "kamulaştırma" in title_lower:
            summary = "Kamu yararı kapsamında acele kamulaştırma işlemi gerçekleştirilmiştir. Bu karar, ulusal projeler ve altyapı yatırımlarının zamanında tamamlanması amacıyla alınmıştır."
        else:
            summary = "İdari İşlem kapsamında yapılan bu düzenleme, ilgili mevzuatın güncellenmesini ve uygulamada birliğin sağlanmasını amaçlamaktadır. Düzenleme, sektör paydaşları ve vatandaşlar için yeni haklar ve yükümlülükler getirmektedir."
        
        return {
            "summary": summary, 
            "category": category,
            "ai_generated": False,
            "fallback_used": True
        }

    def batch_analyze_content(self, content_list: List[Dict]) -> List[Dict[str, Any]]:
        """
        Toplu içerik analizi - performans optimizasyonu
        """
        results = []
        for content in content_list:
            analysis = self.analyze_content_with_autonomous_control(
                content.get("title", ""), 
                content.get("category", "")
            )
            results.append(analysis)
        return results

# Global instance
enhanced_ai_analyzer = EnhancedAIContentAnalyzer()
