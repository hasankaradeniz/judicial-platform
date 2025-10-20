import time
import random
import re
import datetime
from django.core.management.base import BaseCommand

# Selenium & WebDriver Manager (Firefox örneği)
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import (
    StaleElementReferenceException,
    NoSuchElementException,
    TimeoutException
)

from django import db
from core.models import JudicialDecision


class Command(BaseCommand):
    help = (
        "normkararlarbilgibankasi.anayasa.gov.tr adresindeki kararları gezerek veritabanına kaydeder.\n"
        "- Karar Türü: Sabit olarak 'ANAYASA MAHKEMESİ'\n"
        "- Anahtar Kelimeler: Sabit olarak 'NORM DENETİMİ KARARI'\n"
        "- Esas Sayısı: Detay sayfasında 'Esas Sayısı : 2023/66' ifadesinden çekilir\n"
        "- Karar Sayısı: Detay sayfasında 'Karar Sayısı : 2024/185' ifadesinden çekilir\n"
        "- Karar Tarihi: Detay sayfasında 'Karar Tarihi : 5/11/2024' ifadesi çekilerek DB'ye YYYY-MM-DD formatında kaydedilir\n"
        "- Karar Özeti: Detay sayfasındaki tam metinde 'İPTAL DAVASININ KONUSU:' ifadesinden başlayıp, "
        " 'I. İPTALİ İSTENEN' ifadesine kadar olan bölüm\n"
        "- Karar Tam Metni: Detay sayfasındaki metnin tamamı\n"
        "Detay kaydedildikten sonra geri butonuna tıklanır ve listeye dönülüp sonraki karara geçilir.\n"
        "Sayfa altındaki 'Sonraki' (rel='next') linki ile sonraki sayfaya geçilir."
    )

    def extract_detail_data(self, driver):
        """
        Detay sayfasındaki metinden; Esas Sayısı, Karar Sayısı, Karar Tarihi ve Karar Özeti verilerini çıkarır.
        """
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div#Karar.tab-pane.fade.in.active"))
            )
        except TimeoutException:
            self.stdout.write(self.style.WARNING("Karar sekmesi aktif olmadı veya #Karar div'i bulunamadı."))
            return {
                "full_text": "",
                "esas_no": "Bilinmiyor",
                "karar_no": "Bilinmiyor",
                "karar_tarihi": None,
                "karar_ozeti": ""
            }

        try:
            content_elem = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div#Karar div.KararMetni div.WordSection1"))
            )
        except TimeoutException:
            self.stdout.write(self.style.WARNING("KararMetni veya WordSection1 bulunamadı."))
            return {
                "full_text": "",
                "esas_no": "Bilinmiyor",
                "karar_no": "Bilinmiyor",
                "karar_tarihi": None,
                "karar_ozeti": ""
            }

        full_text = content_elem.text.strip()

        # Esas No
        match_esas = re.search(r"Esas Sayısı\s*:\s*([\d/]+)", full_text, re.IGNORECASE)
        esas_no = match_esas.group(1) if match_esas else "Bilinmiyor"

        # Karar No
        match_karar = re.search(r"Karar Sayısı\s*:\s*([\d/]+)", full_text, re.IGNORECASE)
        karar_no = match_karar.group(1) if match_karar else "Bilinmiyor"

        # Karar Tarihi
        match_tarih = re.search(r"Karar Tarihi\s*:\s*([\d/\.]+)", full_text, re.IGNORECASE)
        karar_tarihi = None
        if match_tarih:
            raw_date = match_tarih.group(1)
            for fmt in ("%d/%m/%Y", "%d.%m.%Y"):
                try:
                    karar_tarihi = datetime.datetime.strptime(raw_date, fmt).date()
                    break
                except ValueError:
                    pass

        # Karar Özeti
        summary_match = re.search(
            r"İPTAL DAVASININ KONUSU:\s*(.*?)\s*I\. İPTALİ İSTENEN",
            full_text,
            flags=re.DOTALL | re.IGNORECASE
        )
        if summary_match:
            karar_ozeti = summary_match.group(1).strip()
        else:
            karar_ozeti = full_text[:3000].strip()

        return {
            "full_text": full_text,
            "esas_no": esas_no,
            "karar_no": karar_no,
            "karar_tarihi": karar_tarihi,
            "karar_ozeti": karar_ozeti,
        }

    def click_back(self, driver):
        """Detay sayfasından listeye geri dönmek için geri butonuna tıklar.
           Bulunamazsa kullanıcıdan manuel tıklama bekler."""
        try:
            back_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "div.geri > a"))
            )
            back_button.click()
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Geri butonu bulunamadı veya tıklanamadı: {e}"))
            self.stdout.write("Lütfen geri butonuna manuel tıklayın ve Enter'a basın...")
            input("Devam etmek için Enter'a basınız...")

    def click_element(self, element, driver):
        """Elementi görünür hale getirip JavaScript click ile tıklar.
           Bulunamaz veya tıklanamazsa kullanıcıdan manuel tıklama bekler."""
        attempts = 0
        while attempts < 3:
            try:
                driver.execute_script("arguments[0].scrollIntoView(true);", element)
                time.sleep(0.5)
                driver.execute_script("arguments[0].click();", element)
                return
            except StaleElementReferenceException:
                attempts += 1
                time.sleep(1)

        # 3 denemede de tıklayamazsak manuel müdahale isteyelim
        self.stdout.write(self.style.WARNING("Element stale veya tıklanamadı. Lütfen elle tıklayın."))
        self.stdout.write("Elle tıklama yaptıktan sonra Enter'a basın...")
        input("Devam etmek için Enter'a basınız...")

    def handle(self, *args, **options):
        firefox_options = webdriver.FirefoxOptions()
        # firefox_options.add_argument("--headless")
        firefox_options.add_argument("--no-sandbox")
        firefox_options.add_argument("--disable-dev-shm-usage")

        service = FirefoxService(executable_path=GeckoDriverManager().install())
        driver = webdriver.Firefox(service=service, options=firefox_options)
        driver.get("https://normkararlarbilgibankasi.anayasa.gov.tr")
        self.stdout.write("Tarayıcı açıldı, karar listesi yüklendi.")

        KARAR_TURU = "ANAYASA MAHKEMESİ"
        ANAHTAR_KELIMELER = "NORM DENETİMİ KARARI"

        while True:
            time.sleep(2)
            try:
                karar_blocks = driver.find_elements(By.CSS_SELECTOR, "div.birkarar")
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Karar blokları bulunamadı: {e}"))
                # Kullanıcıya manuel müdahale şansı verelim
                self.stdout.write("Lütfen karar listesinin yüklü olduğundan emin olun ve Enter'a basın...")
                input()
                # Tekrar denemek isterseniz continue edebilirsiniz
                continue

            if not karar_blocks:
                self.stdout.write(self.style.WARNING("Karar listesi boş veya son sayfa olabilir."))
                break

            index = 0
            while index < len(karar_blocks):
                try:
                    # Tekrar karar bloklarını al
                    karar_blocks = driver.find_elements(By.CSS_SELECTOR, "div.birkarar")
                    block = karar_blocks[index]
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"Karar bloğu alınamadı: {e}"))
                    index += 1
                    continue

                # Detay linkine tıklama
                try:
                    karar_link = block.find_element(By.CSS_SELECTOR, "a.waves-effect")
                    self.click_element(karar_link, driver)
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"Karar linki tıklanamadı: {e}"))
                    self.stdout.write("Lütfen karar detayına manuel tıklayın ve Enter'a basın...")
                    input("Devam etmek için Enter'a basınız...")

                # Detay sayfasının yüklenmesini bekle
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div#Karar.tab-pane.fade.in.active"))
                    )
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"Detay sayfası yüklenmedi veya #Karar aktif olmadı: {e}"))
                    self.stdout.write("Lütfen karar detayının gerçekten açıldığından emin olun ve Enter'a basın...")
                    input()
                    # Yine de veri çekmeyi deniyoruz
                time.sleep(random.uniform(1, 2))

                # Veri çek
                try:
                    detail_data = self.extract_detail_data(driver)
                    # Veritabanı kaydı
                    db.connections.close_all()

                    JudicialDecision.objects.create(
                        karar_turu=KARAR_TURU,
                        karar_veren_mahkeme="Anayasa Mahkemesi",
                        esas_numarasi=(detail_data["esas_no"] + " E.") if detail_data["esas_no"] != "Bilinmiyor" else "Bilinmiyor",
                        karar_numarasi=(detail_data["karar_no"] + " K.") if detail_data["karar_no"] != "Bilinmiyor" else "Bilinmiyor",
                        karar_tarihi=detail_data["karar_tarihi"],
                        anahtar_kelimeler=ANAHTAR_KELIMELER,
                        karar_ozeti=detail_data["karar_ozeti"],
                        karar_tam_metni=detail_data["full_text"],
                    )
                    self.stdout.write(self.style.SUCCESS("Karar başarıyla kaydedildi!"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Detay sayfasından veri çekilirken hata: {e}"))

                # Geri dön
                try:
                    self.click_back(driver)
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"Geri butonuna tıklanırken hata: {e}"))
                    self.stdout.write("Lütfen tarayıcıda geri butonuna veya listeye manuel dönüp Enter'a basın...")
                    input("Devam etmek için Enter'a basınız...")

                time.sleep(random.uniform(1, 2))
                index += 1

            # Sonraki sayfa
            try:
                next_link = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//li/a[@rel='next']"))
                )
                next_link.click()
                self.stdout.write(self.style.SUCCESS("Sonraki sayfaya geçiliyor..."))
                time.sleep(2)
            except (NoSuchElementException, TimeoutException) as e:
                self.stdout.write(self.style.WARNING(f"Sonraki sayfa linki bulunamadı veya tıklanamadı: {e}"))
                self.stdout.write("Lütfen sayfadaki 'Sonraki' linkine manuel olarak tıklayın ve ardından Enter tuşuna basın...")
                input("Devam etmek için Enter'a basınız...")
                # Manuel tıklamadan sonra yine continue diyerek döngüye devam edebilirsiniz
                continue

        driver.quit()
        self.stdout.write("Tarayıcı kapatıldı, işlem tamamlandı.")
