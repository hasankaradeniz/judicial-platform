import time
import datetime
import re
import random
from django.core.management.base import BaseCommand

# --- Chrome için gerekli importlar ---
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

from django import db  # Bağlantıyı yenilemek için
from core.models import JudicialDecision

def human_like_mouse_move(actions, start_x, start_y, end_x, end_y, steps=10):
    delta_x = (end_x - start_x) / steps
    delta_y = (end_y - start_y) / steps
    for i in range(steps):
        actions.move_by_offset(delta_x, delta_y).perform()
        time.sleep(random.uniform(0.1, 0.3))
    actions.reset_actions()

class Command(BaseCommand):
    help = (
        "Chrome tarayıcısı kullanılarak emsal.uyap.gov.tr sitesindeki Bölge Adliye Mahkemesi kararlarını çekip "
        "veritabanına kaydeder.\n"
        "- Karar Türü: 'BÖLGE ADLİYE MAHKEMESİ' (sabit)\n"
        "- Mahkeme: Header bilgisinden alınır (ör: 'T.C. ANKARA BÖLGE ADLİYE MAHKEMESİ ...')\n"
        "- Esas Numarası: Header'da 'DOSYA NO :' veya 'ESAS NO :' ifadesinden çekilir ve 'E.' eki eklenir\n"
        "- Karar Numarası: Header'da 'KARAR NO :' ifadesinden çekilir ve 'K.' eki eklenir\n"
        "- Karar Tarihi: Metin içinde bulunan son dd.mm.yyyy formatındaki tarih, DB'ye YYYY-MM-DD olarak kaydedilir\n"
        "- Anahtar Kelimeler: 'Taraflar arasında' veya 'Taraflar arasındaki' ifadesini içeren satır\n"
        "- Karar Özeti: Metinde en son geçen 'HÜKÜM :' ifadesinden önceki son üç paragraf (bulunamazsa son 1000 karakter)\n"
        "- Karar Tam Metni: Sağ paneldeki metnin tamamı\n"
        "Her 40 karar çekildikten sonra 5 dakika beklenir."
    )

    def handle(self, *args, **options):
        # Chrome seçeneklerini ayarlıyoruz (Headless mod istenirse uncomment edin)
        chrome_options = webdriver.ChromeOptions()
        # chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

        # Chrome driver'ı başlatıyoruz
        service = ChromeService(executable_path=ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.get("https://emsal.uyap.gov.tr")

        self.stdout.write("Tarayıcı açıldı. Soldan karar seçip sağ panelde görüntüleyin.")
        self.stdout.write("Sağ tıklayarak açılan menüde 'Kararı Kaydet' seçeneğine basın.")
        self.stdout.write("Program otomatik olarak her döngüde insan benzeri davranışlar sergileyecek. Çıkmak için Ctrl+C kullanın.")

        # Sağ tık menüsü enjekte et
        custom_menu_script = r"""
        (function(){
            if (window.customMenuInjected) return;
            window.customMenuInjected = true;
            window.kararIcerik = "";
            var menu = document.createElement('div');
            menu.id = 'customContextMenu';
            menu.style.display = 'none';
            menu.style.position = 'fixed';
            menu.style.zIndex = '999999';
            menu.style.backgroundColor = '#eee';
            menu.style.border = '1px solid #333';
            menu.style.padding = '5px';
            menu.style.fontFamily = 'Arial, sans-serif';
            var kaydetItem = document.createElement('div');
            kaydetItem.innerText = 'Kararı Kaydet';
            kaydetItem.style.padding = '5px 10px';
            kaydetItem.style.cursor = 'pointer';
            kaydetItem.addEventListener('click', function(e) {
                e.stopPropagation();
                var contentDiv = document.querySelector('#kararAlani .card-scroll');
                var contentText = contentDiv ? contentDiv.innerText : "";
                window.kararIcerik = contentText;
                alert('Karar içeriği kaydedilmek üzere ayarlandı!');
                menu.style.display = 'none';
            });
            menu.appendChild(kaydetItem);
            document.body.appendChild(menu);
            var kararArea = document.getElementById('kararAlani') || document.body;
            kararArea.addEventListener('contextmenu', function(e){
                e.preventDefault();
                menu.style.left = e.pageX + 'px';
                menu.style.top = e.pageY + 'px';
                menu.style.display = 'block';
            });
            document.addEventListener('click', function(){
                menu.style.display = 'none';
            });
        })();
        """
        driver.execute_script(custom_menu_script)
        self.stdout.write("Özel sağ tık menüsü eklendi. Sağ panelde karara sağ tıklayın, 'Kararı Kaydet' seçeneğini seçin.")

        actions = ActionChains(driver)
        decision_count = 0

        try:
            while True:
                decision_count += 1
                delay = random.uniform(2, 4)
                if decision_count % 50 == 0:
                    self.stdout.write(self.style.WARNING("50 karar çekildi, ekstra 10 saniye bekleniyor..."))
                    delay += 10
                time.sleep(delay)

                window_size = driver.get_window_size()
                width = window_size.get('width', 800)
                height = window_size.get('height', 600)
                start_x = random.randint(0, width - 1)
                start_y = random.randint(0, height - 1)
                end_x = random.randint(0, width - 1)
                end_y = random.randint(0, height - 1)
                try:
                    human_like_mouse_move(actions, start_x, start_y, end_x, end_y, steps=10)
                except Exception as e:
                    self.stdout.write(self.style.WARNING("Fare hareketinde hata: " + str(e)))

                scroll_offset = random.randint(-200, 200)
                driver.execute_script("window.scrollBy(0, arguments[0]);", scroll_offset)

                try:
                    scroll_container = driver.find_element(By.CSS_SELECTOR, "#kararAlani .card-scroll")
                    drag_distance = random.randint(50, 150)
                    actions.click_and_hold(scroll_container).move_by_offset(0, drag_distance).release().perform()
                    actions.reset_actions()
                except Exception as e:
                    self.stdout.write(self.style.WARNING("Kaydırma alanında drag işleminde hata: " + str(e)))

                try:
                    alert = driver.switch_to.alert
                    alert.accept()
                except Exception:
                    pass

                driver.execute_script("""
                    if(document.querySelector('#kararAlani .card-scroll')){
                        window.kararIcerik = document.querySelector('#kararAlani .card-scroll').innerText;
                    }
                """)
                js_code = r"""
                    var result = null;
                    if (window.kararIcerik && window.kararIcerik.trim() !== "") {
                        result = { kararMetni: window.kararIcerik.trim() };
                    }
                    return result;
                """
                data = driver.execute_script(js_code)
                if data and data.get("kararMetni"):
                    full_text = data["kararMetni"].lstrip()

                    karar_turu = "YARGITAY"
                    lines = full_text.splitlines()
                    mahkeme = "Yargıtay Bilinmiyor"
                    esas_numarasi = "Bilinmiyor"
                    karar_numarasi = "Bilinmiyor"
                    if lines:
                        header_line = lines[0].strip()
                        if "esas-karar no:" in header_line.lower():
                            mahkeme = header_line.split("Esas-Karar No:")[0].strip()
                        else:
                            mahkeme = header_line
                    for line in lines:
                        line_stripped = line.strip()
                        match_dosya = re.search(r'DOSYA\s+NO\s*:\s*(\d+/\d+)', line_stripped, re.IGNORECASE)
                        if match_dosya:
                            raw_dosya = match_dosya.group(1).strip()
                            esas_numarasi = f"{raw_dosya} E."
                        else:
                            match_esas = re.search(r'ESAS\s+NO\s*:\s*(\d+/\d+)', line_stripped, re.IGNORECASE)
                            if match_esas:
                                raw_esas = match_esas.group(1).strip()
                                esas_numarasi = f"{raw_esas} E."
                        match_karar = re.search(r'KARAR\s+NO\s*:\s*(\d+/\d+)', line_stripped, re.IGNORECASE)
                        if match_karar:
                            raw_karar = match_karar.group(1).strip()
                            karar_numarasi = f"{raw_karar} K."

                    date_matches = re.findall(r'\b(\d{2}\.\d{2}\.\d{4})\b', full_text)
                    if date_matches:
                        raw_date_str = date_matches[-1]
                        try:
                            parsed_date = datetime.datetime.strptime(raw_date_str, "%d.%m.%Y").date()
                            karar_tarihi = parsed_date
                        except Exception as e:
                            karar_tarihi = None
                            self.stdout.write(self.style.WARNING(f"Tarih dönüştürülemedi: {e}"))
                    else:
                        karar_tarihi = None

                    paragraphs_for_keywords = full_text.split("\n")
                    anahtar_kelimeler = "No data"
                    for par in paragraphs_for_keywords:
                        if "taraflar arasında" in par.lower() or "taraflar arasındaki" in par.lower():
                            anahtar_kelimeler = par.strip()
                            break

                    paragraphs = re.split(r'\n\s*\n', full_text)
                    index_of_hukum = None
                    for i in reversed(range(len(paragraphs))):
                        if re.search(r'\bHÜKÜM\s*:\s*', paragraphs[i], re.IGNORECASE):
                            index_of_hukum = i
                            break
                    if index_of_hukum is not None and index_of_hukum > 0:
                        start_par = max(0, index_of_hukum - 3)
                        summary_pars = paragraphs[start_par:index_of_hukum]
                        karar_ozeti = "\n\n".join(summary_pars).strip()
                        if not karar_ozeti:
                            karar_ozeti = full_text[-3000:]
                    else:
                        karar_ozeti = full_text[-3000:]

                    full_text_cleaned = full_text.strip()

                    from django import db
                    db.connections.close_all()
                    JudicialDecision.objects.create(
                        karar_turu=karar_turu,
                        karar_veren_mahkeme=mahkeme,
                        esas_numarasi=esas_numarasi,
                        karar_numarasi=karar_numarasi,
                        karar_tarihi=karar_tarihi,
                        anahtar_kelimeler=anahtar_kelimeler,
                        karar_ozeti=karar_ozeti,
                        karar_tam_metni=full_text_cleaned
                    )
                    self.stdout.write(self.style.SUCCESS("Karar verileri başarıyla kaydedildi!"))
                    decision_count += 1

                    if decision_count >= 40:
                        self.stdout.write(self.style.WARNING("40 karar çekildi, 5 dakika bekleniyor..."))
                        time.sleep(100)
                        decision_count = 0

                    try:
                        next_button = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, "//a[contains(@onclick, 'moveNext()')]"))
                        )
                        next_button.click()
                        self.stdout.write(self.style.SUCCESS("Sonraki Karara geçildi."))
                        time.sleep(random.uniform(1, 2))
                    except Exception as e:
                        self.stdout.write(self.style.WARNING("Sonraki Karar butonuna ulaşılamadı: " + str(e)))
                        break

                    driver.execute_script("window.kararIcerik = ''")
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("İşlem kullanıcı tarafından durduruldu."))
        finally:
            driver.quit()
            self.stdout.write("Tarayıcı kapatıldı.")
