import time
import datetime
import re
import random
from django.core.management.base import BaseCommand

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

from django import db
from core.models import JudicialDecision

def human_like_mouse_move(actions, start_x, start_y, end_x, end_y, steps=10):
    delta_x = (end_x - start_x) / steps
    delta_y = (end_y - start_y) / steps
    for i in range(steps):
        actions.move_by_offset(delta_x, delta_y).perform()
        time.sleep(random.uniform(0.1, 0.3))
    actions.reset_actions()

class Command(BaseCommand):
    help = "Yargıtay kararlarını eksiksiz ve hatada kullanıcı müdahalesiyle çeker, son karar çekilince işlemi bitirir. Sadece Chrome kullanır ve insansı beklemeler içerir."

    def handle(self, *args, **options):
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.5672.63 Safari/537.36",
            "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36",
        ]
        selected_user_agent = random.choice(user_agents)

        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument(f"user-agent={selected_user_agent}")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        #chrome_options.add_argument("--headless")  # Gerekirse başsız mod

        service = ChromeService(executable_path=ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.get("https://karararama.yargitay.gov.tr")

        self.stdout.write("Tarayıcı açıldı. Soldan karar seçip sağ panelde görüntüleyin.")
        self.stdout.write("Sağ tıklayarak açılan menüde 'Kararı Kaydet' seçeneğine basın.")
        self.stdout.write("Çıkmak için Ctrl+C kullanın.")

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
        last_saved_esas_no = None
        last_saved_karar_no = None

        try:
            while True:
                try:
                    decision_count += 1

                    # --- İNSAN BENZERİ ve RASTGELE BEKLEMELER ---
                    # Kararlar arasında 2-5 sn rastgele bekle
                    time.sleep(random.uniform(2, 5))

                    # Her 40 kararda 2 dakika bekle
                    if decision_count > 0 and decision_count % 40 == 0:
                        self.stdout.write(self.style.WARNING("40 karar çekildi. 2 dakika bekleniyor..."))
                        time.sleep(100)

                    # Her 70 kararda 5 dakika bekle
                    if decision_count > 0 and decision_count % 70 == 0:
                        self.stdout.write(self.style.WARNING("70 karar çekildi. 5 dakika bekleniyor..."))
                        time.sleep(150)

                    # İnsan benzeri mouse hareketi (hata olursa sessizce geç)
                    window_size = driver.get_window_size()
                    width = window_size.get('width', 800)
                    height = window_size.get('height', 600)
                    start_x = random.randint(0, width - 1)
                    start_y = random.randint(0, height - 1)
                    end_x = random.randint(0, width - 1)
                    end_y = random.randint(0, height - 1)
                    try:
                        human_like_mouse_move(actions, start_x, start_y, end_x, end_y, steps=10)
                    except Exception:
                        pass

                    # Rastgele sayfa kaydırma
                    scroll_offset = random.randint(-200, 200)
                    driver.execute_script("window.scrollBy(0, arguments[0]);", scroll_offset)

                    try:
                        scroll_container = driver.find_element(By.CSS_SELECTOR, "#kararAlani .card-scroll")
                        drag_distance = random.randint(50, 150)
                        actions.click_and_hold(scroll_container).move_by_offset(0, drag_distance).release().perform()
                        actions.reset_actions()
                    except Exception as e:
                        self.stdout.write(self.style.WARNING("Kaydırma alanında drag işleminde hata: " + str(e)))

                    # Alert varsa kapat
                    try:
                        alert = driver.switch_to.alert
                        alert.accept()
                    except Exception:
                        pass

                    # Kararı otomatik çek
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

                        # Header'dan esas/karar numarası yakala
                        lines = full_text.splitlines()
                        if lines:
                            header_line = lines[0].strip()
                            match = re.search(r'^(.*?)\s+(\d+\/\d+\s*E\.)\s*,\s*(\d+\/\d+\s*K\.)', header_line)
                            if match:
                                mahkeme = "Yargıtay " + match.group(1).strip()
                                esas_numarasi = match.group(2).strip()
                                karar_numarasi = match.group(3).strip()
                            else:
                                mahkeme = "Yargıtay Bilinmiyor"
                                esas_numarasi = "Bilinmiyor"
                                karar_numarasi = "Bilinmiyor"
                        else:
                            mahkeme = "Yargıtay Bilinmiyor"
                            esas_numarasi = "Bilinmiyor"
                            karar_numarasi = "Bilinmiyor"

                        # Karar tarihini bul
                        date_matches = re.findall(r'\b(\d{2}\.\d{2}\.\d{4})\b', full_text)
                        karar_tarihi = None
                        if date_matches:
                            raw_date_str = date_matches[-1]
                            try:
                                parsed_date = datetime.datetime.strptime(raw_date_str, "%d.%m.%Y").date()
                                karar_tarihi = parsed_date
                            except Exception as e:
                                karar_tarihi = None
                                self.stdout.write(self.style.WARNING(f"Tarih dönüştürülemedi: {e}"))

                        # Anahtar kelimeler ve özet çıkarımı
                        paragraphs_for_keywords = full_text.split("\n")
                        anahtar_kelimeler = "No data"
                        for par in paragraphs_for_keywords:
                            if "taraflar arasında" in par.lower() or "taraflar arasındaki" in par.lower():
                                anahtar_kelimeler = par.strip()
                                break

                        paragraphs = re.split(r'\n\s*\n', full_text)
                        index_of_aciklanan = None
                        for i, p in enumerate(paragraphs):
                            if re.search(r'(açıklanan sebeplerle|açıklanan nedenlerle)', p, re.IGNORECASE):
                                index_of_aciklanan = i
                                break
                        if index_of_aciklanan is not None and index_of_aciklanan > 0:
                            start_par = max(0, index_of_aciklanan - 3)
                            summary_pars = paragraphs[start_par:index_of_aciklanan]
                            karar_ozeti = "\n\n".join(summary_pars).strip()
                            if not karar_ozeti:
                                karar_ozeti = full_text[-1000:]
                        else:
                            karar_ozeti = full_text[-1000:]

                        db.connections.close_all()
                        JudicialDecision.objects.create(
                            karar_turu="YARGITAY",
                            karar_veren_mahkeme=mahkeme,
                            karar_tarihi=karar_tarihi,
                            esas_numarasi=esas_numarasi,
                            karar_numarasi=karar_numarasi,
                            anahtar_kelimeler=anahtar_kelimeler,
                            karar_ozeti=karar_ozeti,
                            karar_tam_metni=full_text
                        )
                        self.stdout.write(self.style.SUCCESS("Karar verileri başarıyla kaydedildi!"))

                        last_saved_esas_no = esas_numarasi
                        last_saved_karar_no = karar_numarasi

                        # Sonraki Karara geç
                        try:
                            next_button = WebDriverWait(driver, 5).until(
                                EC.element_to_be_clickable((By.XPATH, "//a[contains(@onclick, 'moveNext()')]"))
                            )
                            next_button.click()
                            self.stdout.write(self.style.SUCCESS("Sonraki Karara geçildi."))
                            time.sleep(random.uniform(1, 2))
                        except Exception as e:
                            self.stdout.write(self.style.WARNING("Sonraki Karar butonuna ulaşılamadı: " + str(e)))
                            self.stdout.write(self.style.WARNING("Muhtemelen son sayfadasınız, son karar kontrolü yapılıyor..."))
                            # SON KARAR KONTROLÜ: Son karardan sonra sayfa yoksa güvenle çık
                            break

                        driver.execute_script("window.kararIcerik = ''")
                    else:
                        self.stdout.write(self.style.WARNING("Karar metni çekilemedi veya boş geldi!"))
                        input("Devam etmek için ENTER'a basın veya çıkmak için Ctrl+C...")
                        continue

                except Exception as main_e:
                    self.stdout.write(self.style.WARNING(f"Hata oluştu: {main_e}"))
                    input("Bir hata oluştu. Devam etmek için ENTER'a basın veya çıkmak için Ctrl+C...")
                    continue

        except KeyboardInterrupt:
            self.stdout.write("⛔ İşlem kullanıcı tarafından durduruldu.")
        finally:
            driver.quit()
            self.stdout.write("🧹 Tarayıcı kapatıldı, işlem tamamlandı.")
