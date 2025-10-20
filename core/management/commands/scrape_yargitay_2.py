import time
import datetime
import re
import random
import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand

# Selenium ve WebDriver Manager importları
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

# Tarayıcı parmak izi çeşitlendirme için selenium-stealth importu
from selenium_stealth import stealth

from django import db  # Bağlantıyı yenilemek için
from core.models import JudicialDecision


def get_free_proxies():
    """
    free-proxy-list.net sitesinden HTTPS proxy'leri çeker.
    Dönüş değeri; kullanılabilir proxy URL'lerinin (http://ip:port) listesidir.
    """
    url = 'https://free-proxy-list.net/'
    proxies = []
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table', id='proxylisttable')
        if table:
            rows = table.tbody.find_all('tr')
            for row in rows:
                cols = row.find_all('td')
                ip = cols[0].text.strip()
                port = cols[1].text.strip()
                https = cols[6].text.strip()
                # Sadece HTTPS (veya isterseniz anonim) proxy'leri ekleyelim
                if https.lower() == "yes":
                    proxies.append(f"http://{ip}:{port}")
    except Exception as e:
        print(f"Proxy listesi alınırken hata: {e}")
    return proxies


def human_like_mouse_move(actions, start_x, start_y, end_x, end_y, steps=10):
    delta_x = (end_x - start_x) / steps
    delta_y = (end_y - start_y) / steps
    for i in range(steps):
        actions.move_by_offset(delta_x, delta_y).perform()
        time.sleep(random.uniform(0.1, 0.3))
    actions.reset_actions()


class Command(BaseCommand):
    help = (
        "Sağ paneldeki karar detayını, sol paneldeki header bilgisini ve metin içerisindeki tarih, özet gibi bilgileri "
        "çıkararak, kararın tüm alanlarını doldurur.\n"
        "- Karar Türü: 'YARGITAY' (sabit)\n"
        "- Mahkeme: Tam metnin en başındaki header'dan (örnek: 'Büyük Genel Kurulu') alınıp 'Yargıtay' önekiyle\n"
        "- Esas Numarası: Header'daki '2022/1 E.' ifadesi\n"
        "- Karar Numarası: Header'daki '2022/1 K.' ifadesi\n"
        "- Karar Tarihi: Metin içinde bulunan son dd.mm.yyyy formatındaki tarih, DB'ye DateField (YYYY-MM-DD) olarak kaydedilir\n"
        "- Anahtar Kelimeler: 'Taraflar arasında' veya 'Taraflar arasındaki' ifadesini içeren satırın tamamı\n"
        "- Karar Özeti: Metinde 'Açıklanan sebeplerle' veya 'Açıklanan nedenlerle' ifadesinden önceki 3 paragraf "
        "(bulunamazsa o ifadelere kadar olan son 1000 karakter)\n"
        "- Karar Tam Metni: Sağ paneldeki metnin tamamı\n"
        "Ek olarak, her 40 karar çekildikten sonra 5 dakika beklenir."
    )

    def handle(self, *args, **options):
        # --- Otomatik Proxy Listesi Çekimi ---
        proxy_list = get_free_proxies()
        if proxy_list:
            selected_proxy = random.choice(proxy_list)
            self.stdout.write(self.style.SUCCESS(f"Rastgele seçilen proxy: {selected_proxy}"))
        else:
            selected_proxy = None
            self.stdout.write(self.style.WARNING("Kullanılabilir proxy bulunamadı, proxy kullanılmayacak."))

        # Kullanılacak farklı user-agent stringlerini içeren liste
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.5672.63 Safari/537.36",
            "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36",
        ]
        selected_user_agent = random.choice(user_agents)

        # ChromeOptions ile user-agent bilgisini ayarlıyoruz
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument(f"user-agent={selected_user_agent}")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        # Eğer headless mod kullanmak isterseniz, aşağıdaki satırı uncomment edebilirsiniz:
        # chrome_options.add_argument("--headless")

        # --- Proxy ayarını ekliyoruz ---
        if selected_proxy:
            chrome_options.add_argument(f"--proxy-server={selected_proxy}")

        service = ChromeService(executable_path=ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)

        # --- Tarayıcı Parmak İzi Çeşitlendirme (Fingerprint) ---
        stealth(driver,
                user_agent=selected_user_agent,
                languages=["tr-TR", "tr"],
                vendor="Google Inc.",
                platform="Win32",  # İhtiyaca göre "MacIntel" veya "Linux x86_64" gibi ayarlanabilir
                webgl_vendor="Intel Inc.",
                renderer="Intel Iris OpenGL Engine",
                fix_hairline=True,
        )

        driver.get("https://karararama.yargitay.gov.tr")

        self.stdout.write("Tarayıcı açıldı. Soldan karar seçip sağ panelde görüntüleyin.")
        self.stdout.write("Sağ tıklayarak açılan menüde 'Kararı Kaydet' seçeneğine basın.")
        self.stdout.write("Program otomatik olarak her döngüde insan benzeri davranışlar sergileyecek. Çıkmak için Ctrl+C kullanın.")

        # Sağ tık menüsünü enjekte et
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

        while True:
            try:
                decision_count += 1

                # --- İstek Aralıklarını İnsan Benzeri Hale Getirme ---
                delay = random.uniform(2, 4)
                if decision_count % 50 == 0:
                    self.stdout.write(self.style.WARNING("50 karar çekildi, ekstra 10 saniye bekleniyor..."))
                    delay += 10
                time.sleep(delay)

                # İnsan benzeri fare hareketi
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

                # Rastgele global sayfa kaydırması
                scroll_offset = random.randint(-200, 200)
                driver.execute_script("window.scrollBy(0, arguments[0]);", scroll_offset)

                # Sağ paneldeki kaydırılabilir alan üzerinde drag işlemi
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

                # Otomatik olarak sağ paneldeki metni al
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

                    # 1. Karar Türü (sabit)
                    karar_turu = "YARGITAY"

                    # 2. Header'dan: Mahkeme, Esas Numarası, Karar Numarası
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

                    # 3. Karar Tarihi: Metindeki son dd.mm.yyyy ifadesi
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

                    # 4. Anahtar Kelimeler
                    paragraphs_for_keywords = full_text.split("\n")
                    anahtar_kelimeler = "No data"
                    for par in paragraphs_for_keywords:
                        if "taraflar arasında" in par.lower() or "taraflar arasındaki" in par.lower():
                            anahtar_kelimeler = par.strip()
                            break

                    # 5. Karar Özeti
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

                    # 6. Karar Tam Metni
                    db.connections.close_all()
                    JudicialDecision.objects.create(
                        karar_turu=karar_turu,
                        karar_veren_mahkeme=mahkeme,
                        karar_tarihi=karar_tarihi,
                        esas_numarasi=esas_numarasi,
                        karar_numarasi=karar_numarasi,
                        anahtar_kelimeler=anahtar_kelimeler,
                        karar_ozeti=karar_ozeti,
                        karar_tam_metni=full_text
                    )
                    self.stdout.write(self.style.SUCCESS("Karar verileri başarıyla kaydedildi!"))

                    if decision_count >= 100:
                        self.stdout.write(self.style.WARNING("40 karar çekildi, 5 dakika bekleniyor..."))
                        time.sleep(100)
                        decision_count = 0

                    # Sonraki karara geçme adımı
                    try:
                        next_button = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, "//a[contains(@onclick, 'moveNext()')]"))
                        )
                        next_button.click()
                        self.stdout.write(self.style.SUCCESS("Sonraki Karara geçildi."))
                        time.sleep(random.uniform(1, 2))
                    except Exception as e:
                        self.stdout.write(self.style.WARNING("Sonraki Karar butonuna ulaşılamadı: " + str(e)))
                        self.stdout.write("Hata oluştu. Devam etmek için Enter'a basın, çıkmak için 'q' girin.")
                        user_input = input()
                        if user_input.lower() == 'q':
                            break

                    driver.execute_script("window.kararIcerik = ''")
            except KeyboardInterrupt:
                self.stdout.write("Çıkış yapılıyor...")
                break
            except Exception as e:
                self.stdout.write(self.style.ERROR("Bir hata oluştu: " + str(e)))
                self.stdout.write("Lütfen müdahale ediniz. Devam etmek için Enter'a basın, çıkmak için 'q' yazıp Enter'a basın.")
                user_input = input()
                if user_input.lower() == 'q':
                    break

        driver.quit()
        self.stdout.write("Tarayıcı kapatıldı.")
