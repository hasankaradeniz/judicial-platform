# Kategorilendirme sistemini düzelt
content_to_add = """
    def _determine_content_type_and_category(self, item):
        \"\"\"
        Scraping verisinden icerik turu ve kategoriyi belirle - Geliştirilmiş versiyon
        \"\"\"
        baslik = item.get("baslik", "").lower()
        kategori = item.get("kategori", "").lower()
        
        # Cumhurbaşkanı kararları için özel kontrol
        if any(word in baslik for word in ["cumhurbaşkanı kararı", "cumhurbaskani karari"]) or "cumhurbaşkani kararlari" in kategori:
            return "yurutme_idare", "cumhurbaskani_karari"
        elif any(word in baslik for word in ["cumhurbaşkanlığına vekalet", "cumhurbaskanligi", "cumhurbaşkanlığı"]):
            return "yurutme_idare", "cumhurbaskani_karari"
        elif any(word in baslik for word in ["atama kararı", "atama karari"]):
            return "yurutme_idare", "atama_karari"
        elif any(word in baslik for word in ["yönetmelik", "yonetmelik"]):
            return "yurutme_idare", "yonetmelik"
        elif any(word in baslik for word in ["tebliğ", "teblig"]):
            return "yurutme_idare", "teblig"
        elif any(word in baslik for word in ["genelge"]):
            return "yurutme_idare", "genelge"
        elif any(word in baslik for word in ["bakanlar kurulu"]):
            return "yurutme_idare", "bakanlar_kurulu_karari"
        elif any(word in baslik for word in ["kurul kararı", "kurul karari"]):
            return "yurutme_idare", "kurul_karari"
        elif any(word in baslik for word in ["anayasa mahkemesi"]):
            return "anayasa_mahkemesi", "mahkeme_karari"
        elif any(word in baslik for word in ["yargitay", "yargıtay"]):
            return "yargitay", "mahkeme_karari"
        elif any(word in baslik for word in ["danistay", "danıştay"]):
            return "danistay", "mahkeme_karari"
        elif any(word in baslik for word in ["ilan", "ihale", "artırma"]):
            return "ilan", "ilan"
        else:
            return "yurutme_idare", "diger_islemler"
            
    def _create_enhanced_summary(self, item, category):
        \"\"\"
        İçerik için genişletilmiş özet oluştur
        \"\"\"
        title_lower = item.title.lower()
        
        if category == "Cumhurbaşkanı Kararı":
            if "vekalet" in title_lower:
                return "Cumhurbaşkanlığına vekalet etme yetkisi ile ilgili düzenleme yapılmıştır. Bu karar, devlet yönetiminin devamlılığını sağlamaya yönelik önemli bir idari işlemdir."
            elif "atama" in title_lower:
                return "Cumhurbaşkanı tarafından kamu görevlilerinin atanması ile ilgili karar alınmıştır. Bu düzenleme, kamu yönetimindeki personel değişikliklerini kapsamaktadır."
            elif "enerji" in title_lower or "elektrik" in title_lower:
                return "Enerji sektörü ile ilgili Cumhurbaşkanı kararı yayımlanmıştır. Bu düzenleme, enerji altyapısı ve yatırımları konusunda önemli gelişmeleri içermektedir."
            elif "vergi" in title_lower:
                return "Vergi düzenlemeleri kapsamında Cumhurbaşkanı kararı çıkarılmıştır. Bu karar, vergi politikaları ve uygulamaları açısından önem taşımaktadır."
            else:
                return "Cumhurbaşkanı tarafından çıkarılan bu karar, kamu yönetimi ve düzenleyici işlemler kapsamında önemli değişiklikler içermektedir."
        elif category == "Yönetmelik":
            return "Yeni yönetmelik düzenlemesi ile ilgili kurallar ve uygulamalar güncellenmiştir. Bu düzenleme, ilgili sektör ve kurumlarda uygulanacak prosedürleri belirlemektedir."
        elif category == "Tebliğ":
            return "İlgili kurum tarafından yayımlanan tebliğ ile uygulamaya yönelik açıklamalar ve yönlendirmeler yapılmıştır."
        elif category == "Atama Kararı":
            return "Kamu kurum ve kuruluşlarında personel atama işlemleri gerçekleştirilmiştir. Bu atamalar, kurumsal yapılanma ve yönetim kadroları açısından önem taşımaktadır."
        elif category == "Genelge":
            return "İlgili kurum tarafından yayımlanan genelge ile uygulama birliği sağlanması ve prosedürlerin netleştirilmesi amaçlanmıştır."
        else:
            return f"{category} kapsamında yapılan bu düzenleme, ilgili mevzuat ve uygulamalar açısından güncel gelişmeleri içermektedir."
"""

# Dosyayı oku
with open("core/daily_gazette_service.py", "r", encoding="utf-8") as f:
    content = f.read()

# Eski fonksiyonları bul ve değiştir
import re

# _determine_content_type_and_category fonksiyonunu değiştir
pattern = r"def _determine_content_type_and_category\(self, item\):.*?(?=    def|\Z)"
content = re.sub(pattern, content_to_add.strip(), content, flags=re.DOTALL)

# Dosyayı yaz
with open("core/daily_gazette_service.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Kategorilendirme sistemi güncellendi")
