import time
import random
import re
import datetime
from django.core.management.base import BaseCommand

# Selenium ve WebDriver Manager importları
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import ElementClickInterceptedException, TimeoutException, WebDriverException

from django import db
from core.models import JudicialDecision  # Projenize göre modeli uyarlayın


class Command(BaseCommand):
    help = (
        "T.C. Sayıştay Başkanlığı Daire Kararları sayfasından kararları çekerek veritabanına kaydeder.\n"
        "- Karar Türü: 'SAYIŞTAY' (sabit)\n"
        "- Kararı Veren Mahkeme: 'Sayıştay X. Dairesi' (Daire değeri çekilir)\n"
        "- Karar Tarihi: Detay sayfasındaki 'Karar Tarihi' (dd.mm.yyyy formatında)\n"
        "- Karar No: Detay sayfasındaki 'Karar No' değeri\n"
        "- İlam No: Detay sayfasındaki 'İlam No' değeri, veritabanına 'İlam No: X' formatında kaydedilir\n"
        "- Karar Metni: \n"
        "    * İlk paragraf → anahtar_kelimeler\n"
        "    * Sonraki iki paragraf → karar_ozeti\n"
        "    * Tam metin → karar_tam_metni\n"
        "- Listeye Dön butonuyla listeye geri dönülür.\n"
        "Yeni karar bulunamazsa 'Sonraki' sayfaya geçilir.\n"
        "Eğer tıklama sırasında başka bir öğe engelliyorsa, JavaScript ile tıklama zorlanır.\n"
        "Sayfa yüklenme süresi 300 saniyeye çıkarılmıştır.\n"
        "Not: Eğer sistem kaynakları yetersizse, ChromeDriver süreci SIGKILL ile sonlandırılabilir (status code -9)."
    )

    def get_value_by_label(self, driver, label_text):
        """
        <div class="row"> içerisindeki soldaki <div class="col-3"> öğesinde yer alan metni
        (örn. <div class="col-3"><b>Daire</b></div>) normalize-space(.) kullanarak kontrol eder
        ve aynı satırdaki sağdaki <div class="col-9"> öğesinin değerini döndürür.
        """
        xpath = (
            f"//div[@class='row'][.//div[contains(@class, 'col-3') and normalize-space(.)='{label_text}']]"
            f"//div[contains(@class, 'col-9')]"
        )
        element = driver.find_element(By.XPATH, xpath)
        return element.text.strip()

    def click_element(self, element, driver):
        """
        Normal click denemesi yapar; eğer ElementClickInterceptedException alınırsa,
        öğeyi scrollIntoView yapıp JavaScript click ile tıklar.
        """
        try:
            element.click()
        except ElementClickInterceptedException:
            driver.execute_script("arguments[0].scrollIntoView(true);", element)
            time.sleep(0.5)
            driver.execute_script("arguments[0].click();", element)

    def handle(self, *args, **options):
        # Opsiyonel: Chrome'u headless modda çalıştırmak için:
        chrome_options = webdriver.ChromeOptions()
        # Uncomment aşağıdaki satırı headless modda çalıştırmak için:
        # chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')

        # ChromeDriverManager().install() tarafından dönen yolu ChromeService ile sarmalıyoruz.
        service = ChromeService(executable_path=ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)

        # Sayfa yükleme zaman aşımını 300 saniyeye ayarlıyoruz.
        driver.set_page_load_timeout(300)

        url = "https://www.sayistay.gov.tr/KararlarDaire"
        driver.get(url)
        self.stdout.write(f"{url} adresine gidildi.")

        # İşlenmiş kararların detay linki href'lerini saklamak için bir set
        processed_decisions = set()

        while True:
            time.sleep(random.uniform(1, 2))
            try:
                rows = driver.find_elements(By.XPATH, "//tbody/tr")
            except Exception:
                self.stdout.write(self.style.WARNING("Liste satırları alınamadı. Bekleniyor..."))
                time.sleep(5)
                continue

            new_row = None
            detail_link = None
            for row in rows:
                try:
                    detail_link = row.find_element(By.XPATH, ".//a[contains(@href, '/KararlarDaire/Detay/')]")
                    href = detail_link.get_attribute("href")
                    if href not in processed_decisions:
                        new_row = row
                        break
                except Exception:
                    continue

            if new_row is None:
                self.stdout.write(self.style.WARNING("Mevcut sayfada yeni karar bulunamadı."))
                try:
                    next_page_button = driver.find_element(By.XPATH, "//a[contains(text(), 'Sonraki')]")
                    self.click_element(next_page_button, driver)
                    self.stdout.write(self.style.SUCCESS("Sonraki sayfaya geçiliyor..."))
                    time.sleep(2)
                    continue
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"Sonraki sayfa butonu bulunamadı. Hata: {e}"))
                    time.sleep(5)
                    continue

            href = detail_link.get_attribute("href")
            self.click_element(detail_link, driver)
            time.sleep(random.uniform(1, 2))

            try:
                # Detay sayfasından veri çekme
                karar_turu = "SAYIŞTAY"

                daire_value = self.get_value_by_label(driver, "Daire")
                mahkeme = f"Sayıştay {daire_value}. Dairesi"

                karar_tarihi_str = self.get_value_by_label(driver, "Karar Tarihi")
                try:
                    karar_tarihi = datetime.datetime.strptime(karar_tarihi_str, "%d.%m.%Y").date()
                except Exception as ex:
                    self.stdout.write(self.style.WARNING(f"Karar tarihi dönüştürülemedi: {ex}"))
                    karar_tarihi = None

                karar_no_value = self.get_value_by_label(driver, "Karar No")
                ilam_no_value = self.get_value_by_label(driver, "İlam No")
                esas_numarasi = f"İlam No: {ilam_no_value}"

                metin_element = driver.find_element(By.ID, "metin")
                karar_metni = metin_element.text.strip()

                paragraphs = re.split(r'\n\s*\n', karar_metni)
                paragraphs = [p.strip() for p in paragraphs if p.strip()]
                anahtar_kelimeler = paragraphs[0] if paragraphs else ""
                if len(paragraphs) >= 3:
                    karar_ozeti = "\n\n".join(paragraphs[1:3])
                elif len(paragraphs) == 2:
                    karar_ozeti = paragraphs[1]
                else:
                    karar_ozeti = ""
                karar_tam_metni = karar_metni

                processed_decisions.add(href)

                db.connections.close_all()
                JudicialDecision.objects.create(
                    karar_turu=karar_turu,
                    karar_veren_mahkeme=mahkeme,
                    karar_tarihi=karar_tarihi,
                    esas_numarasi=esas_numarasi,
                    karar_numarasi=karar_no_value,
                    anahtar_kelimeler=anahtar_kelimeler,
                    karar_ozeti=karar_ozeti,
                    karar_tam_metni=karar_tam_metni
                )
                self.stdout.write(self.style.SUCCESS("Yeni karar başarıyla kaydedildi!"))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Detay sayfasından veri çekilirken hata: {e}"))

            try:
                back_button = driver.find_element(By.XPATH, "//a[contains(@href, '/KararlarDaire') and contains(text(), 'Listeye Dön')]")
                self.click_element(back_button, driver)
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Listeye Dön butonu bulunamadı veya tıklanamadı. Hata: {e}"))
                break

        driver.quit()
        self.stdout.write("Tarayıcı kapatıldı, işlem tamamlandı.")
