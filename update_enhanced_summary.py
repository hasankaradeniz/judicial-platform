# Enhanced summary metodunu AI ile güçlendir

content = """    def get_enhanced_summary(self):
        \"\"\"AI destekli geliştirilmiş özet\"\"\"
        # AI servisi lazy import ile import et
        try:
            from .ai_content_analyzer import ai_analyzer
            
            # AI analiz dene
            analysis = ai_analyzer.analyze_content(self.title, self.category)
            if analysis and analysis.get("summary"):
                return analysis["summary"]
                
        except Exception as e:
            # AI başarısız olursa fallback kullan
            pass
        
        # Fallback - mevcut mantık
        title_lower = self.title.lower()
        category = self.category

        if category == "cumhurbaskani_karari":
            if "vekalet" in title_lower:
                return "Cumhurbaşkanlığına vekalet etme yetkisi düzenlenmiştir. Bu karar, devlet yönetiminin kesintisiz sürdürülmesi ve anayasal düzenin korunması açısından kritik önem taşımaktadır."
            elif "enerji" in title_lower or "elektrik" in title_lower:
                return "Enerji sektörü ve altyapı yatırımlarına yönelik düzenleme yapılmıştır. Bu karar, enerji güvenliği ve sürdürülebilir kalkınma hedefleri doğrultusunda alınmış olup, sektördeki şirketler ve yatırımcılar için yeni fırsatlar yaratmaktadır."
            elif "vergi" in title_lower:
                return "Vergi mevzuatında önemli değişiklikler yapılmıştır. Bu düzenleme, mükellefler ve muhasebe meslek mensupları için yeni yükümlülükler getirirken, vergi adaleti ve tahsilat verimliliğinin artırılması hedeflenmektedir."
            elif "sahipsiz hayvan" in title_lower:
                return "Sahipsiz hayvanların korunması ve bakımına yönelik kurumsal yapılanma kararı alınmıştır. Bu düzenleme, hayvan refahı ve toplum sağlığı açısından önemli bir adım niteliğindedir."
            else:
                return "Cumhurbaşkanı tarafından çıkarılan bu karar, kamu yönetimi ve düzenleyici işlemler kapsamında önemli değişiklikler içermektedir. Karar, ilgili sektör ve paydaşları doğrudan etkileyecek niteliktedir."
        elif category == "yonetmelik":
            return "İlgili konuda uygulama birliğini sağlayacak yönetmelik değişikliği yapılmıştır. Bu düzenleme, mevcut uygulamaları standardize ederek hizmet kalitesinin artırılmasını hedeflemektedir."
        elif category == "teblig":
            return "İlgili kurum tarafından yayımlanan tebliğ ile uygulamaya yönelik detaylı açıklamalar ve yönlendirmeler yapılmıştır. Bu tebliğ, sektör paydaşları için önemli rehber niteliğindedir."
        elif category == "atama_karari":
            return "Kamu kurum ve kuruluşlarında üst düzey personel atama işlemleri gerçekleştirilmiştir. Bu atamalar, kurumsal kapasite ve hizmet kalitesinin artırılması amacıyla yapılmıştır."
        elif category == "genelge":
            return "İlgili kurum tarafından yayımlanan genelge ile uygulama birliğinin sağlanması ve prosedürlerin netleştirilmesi amaçlanmıştır. Bu düzenleme, operasyonel verimliliği artıracaktır."
        elif category == "gunluk_sayi":
            return f"{self.gazette_date.strftime(%d.%m.%Y)} tarihli Resmi Gazete günlük sayısı yayımlanmıştır. Bu sayıda yer alan tüm düzenlemelere PDF formatında erişebilir ve detaylı inceleyebilirsiniz."
        else:
            return f"{self.get_category_display()} kapsamında yapılan bu düzenleme, ilgili mevzuatın güncellenmesini ve uygulamada birliğin sağlanmasını amaçlamaktadır. Düzenleme, sektör paydaşları ve vatandaşlar için yeni haklar ve yükümlülükler getirmektedir.\""""

# Dosyayı oku
with open("core/models.py", "r", encoding="utf-8") as f:
    file_content = f.read()

# Eski get_enhanced_summary metodunu değiştir
import re
old_method_pattern = r"def get_enhanced_summary\(self\):.*?(?=\n    def |\n\nclass |\Z)"
file_content = re.sub(old_method_pattern, content.strip(), file_content, flags=re.DOTALL)

# Dosyayı yaz
with open("core/models.py", "w", encoding="utf-8") as f:
    f.write(file_content)

print("Enhanced summary metodu AI ile güçlendirildi")
