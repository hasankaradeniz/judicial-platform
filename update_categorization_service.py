# Daily gazette service kategorilendirmeyi AI ile güçlendir

content = """    def _determine_content_type_and_category(self, item):
        \"\"\"
        AI destekli içerik kategorilendirme
        \"\"\"
        try:
            # AI kategorilendirici import et
            from .ai_categorizer import ai_categorizer
            
            title = item.get("baslik", "")
            scraped_category = item.get("kategori", "")
            
            # AI ile kategorilendirme dene
            content_type, category = ai_categorizer.categorize_content(title, scraped_category)
            
            logger.info(f"AI Kategorilendirme - Başlık: {title[:50]} -> {category}")
            
            return content_type, category
            
        except Exception as e:
            logger.error(f"AI kategorilendirme hatası, fallback kullanılıyor: {e}")
            return self._fallback_categorize(item)
    
    def _fallback_categorize(self, item):
        \"\"\"
        Fallback kategorilendirme
        \"\"\"
        baslik = item.get("baslik", "").lower()
        kategori = item.get("kategori", "").lower()
        
        # Günlük sayı kontrolü
        if "resmi gazete" in baslik and "sayı" in baslik:
            return "yurutme_idare", "gunluk_sayi"
        
        # Yönetmelik kontrolü
        if "yönetmelik" in baslik:
            return "yurutme_idare", "yonetmelik"
        
        # Tebliğ kontrolü
        if "tebliğ" in baslik or "teblig" in baslik:
            return "yurutme_idare", "teblig"
        
        # Cumhurbaşkanlığı vekalet
        if "vekalet" in baslik or "vekâlet" in baslik:
            return "yurutme_idare", "cumhurbaskani_karari"
        
        # İçerik bazlı kategorilendirme
        if any(word in baslik for word in ["enerji", "elektrik", "transformatör"]):
            return "yurutme_idare", "cumhurbaskani_karari"
        
        if "vergi" in baslik:
            return "yurutme_idare", "cumhurbaskani_karari"
        
        if "sahipsiz hayvan" in baslik:
            return "yurutme_idare", "cumhurbaskani_karari"
        
        if "atama" in baslik:
            return "yurutme_idare", "atama_karari"
        
        # Varsayılan
        return "yurutme_idare", "other\""""

# Dosyayı oku
with open("core/daily_gazette_service.py", "r", encoding="utf-8") as f:
    file_content = f.read()

# Eski _determine_content_type_and_category metodunu değiştir
import re
old_method_pattern = r"def _determine_content_type_and_category\(self, item\):.*?(?=\n    def |\n\nclass |\Z)"
file_content = re.sub(old_method_pattern, content.strip(), file_content, flags=re.DOTALL)

# Dosyayı yaz
with open("core/daily_gazette_service.py", "w", encoding="utf-8") as f:
    f.write(file_content)

print("Kategorilendirme servisi AI ile güçlendirildi")
