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
        "- Anahtar Kelimeler: Sabit olarak 'BİREYSEL BAŞVURU' ifadesi, ardından parantez içinde "
        "I. BAŞVURUNUN ÖZETİ sonrası gelen ilk paragrafın metni\n"
        "- Esas Numarası: Detay sayfasında 'Başvuru Numarası: 2020/34532' ifadesinden çekilir\n"
        "- Karar Sayısı: (varsa) Detay sayfasında 'Karar Sayısı : 2024/185' ifadesinden çekilir\n"
        "- Karar Tarihi: Detay sayfasında 'Karar Tarihi : 29/5/2024' ifadesi çekilerek DB'ye YYYY-MM-DD formatında kaydedilir\n"
        "- Karar Özeti: Karar tam metninde 'IV. HÜKÜM' ifadesinden sonrasının, eğer varsa 'KARŞIOY' yazısına kadar olan bölüm\n"
        "- Karar Tam Metni: Detay sayfasındaki metnin tamamı\n"
        "Detay kaydedildikten sonra geri butonuna tıklanır ve listeye dönülüp sonraki karara geçilir.\n"
        "Sayfa altındaki 'Sonraki' (rel='next') linki ile sonraki sayfaya geçilir."
    )

    def extract_detail_data(self, driver):
        """
        Detay sayfasındaki metinden; Başvuru Numarası, Karar Sayısı, Karar Tarihi,
        I. BAŞVURUNUN ÖZETİ sonrası ilk paragraf, hüküm özeti ve tam metni çıkarır.
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
                "anahtar_kelime_paragraf": "",
                "hukum_ozeti": ""
            }
        # Güncelleme: Karar metni artık <span class="kararHtml"> içinde yer alıyor.
        try:
            content_elem = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "span.kararHtml"))
            )
        except TimeoutException:
            self.stdout.write(self.style.WARNING("Karar metni bulunamadı: 'span.kararHtml' öğesi bulunamadı."))
            return {
                "full_text": "",
                "esas_no": "Bilinmiyor",
                "karar_no": "Bilinmiyor",
                "karar_tarihi": None,
                "anahtar_kelime_paragraf": "",
                "hukum_ozeti": ""
            }
        full_text = content_elem.text.strip()

        # Esas No: "Başvuru Numarası: 2020/34532"
        match_esas = re.search(r"Başvuru Numarası\s*:\s*([\d/]+)", full_text, re.IGNORECASE)
        esas_no = match_esas.group(1) if match_esas else "Bilinmiyor"

        # Karar Sayısı
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
                    continue

        # I. BAŞVURUNUN ÖZETİ sonrası ilk paragrafı satır bazında bulalım
        first_paragraph = ""
        lines = full_text.splitlines()
        found = False
        for line in lines:
            if found and line.strip():
                first_paragraph = line.strip()
                break
            if "I. BAŞVURUNUN ÖZETİ" in line.upper():
                found = True

        # Hüküm Özeti: "IV. HÜKÜM" ifadesinden sonrasını çek; eğer "KARŞIOY" varsa oraya kadar,
        # yoksa metnin sonuna kadar.
        match_hukum = re.search(r"IV\. HÜKÜM(.*)", full_text, re.IGNORECASE | re.DOTALL)
        if match_hukum:
            hukum_text = match_hukum.group(1)
            if "KARŞIOY" in hukum_text.upper():
                split_text = re.split(r"KARŞIOY", hukum_text, flags=re.IGNORECASE)
                hukum_ozeti = split_text[0].strip()
            else:
                hukum_ozeti = hukum_text.strip()
        else:
            hukum_ozeti = ""

        return {
            "full_text": full_text,
            "esas_no": esas_no,
            "karar_no": karar_no,
            "karar_tarihi": karar_tarihi,
            "anahtar_kelime_paragraf": first_paragraph,
            "hukum_ozeti": hukum_ozeti,
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

        # Kullanıcının header bölümünden çekmek istediği kararı seçmesi sağlanıyor.
        self.stdout.write("Lütfen header bölümünde çekmek istediğiniz kararı seçin (örneğin, 'BİREYSEL BAŞVURU').")
        self.stdout.write("Seçiminizi yaptıktan sonra ilgili kararlara ait yeni sekme açılacaktır.")
        input("Scraping işleminin başlaması için Enter tuşuna basınız...")

        # Kullanıcı seçim yaptıktan sonra yeni sekme açıldığını varsayarak geçiş yapıyoruz.
        time.sleep(3)
        if len(driver.window_handles) > 1:
            driver.switch_to.window(driver.window_handles[-1])
            self.stdout.write("Yeni sekmeye geçildi. Scraping işlemi bu sekmedeki kararlar üzerinden devam edecek.")
        else:
            self.stdout.write("Yeni sekme açılmadı. Lütfen ilgili kararı seçtikten sonra yeni sekmenin açıldığından emin olun.")
            input("Yeni sekme açıldıktan sonra Enter'a basınız...")
            driver.switch_to.window(driver.window_handles[-1])

        while True:
            time.sleep(2)
            try:
                karar_blocks = driver.find_elements(By.CSS_SELECTOR, "div.birkarar")
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Karar blokları bulunamadı: {e}"))
                self.stdout.write("Lütfen karar listesinin yüklü olduğundan emin olun ve Enter'a basın...")
                input()
                continue

            if not karar_blocks:
                self.stdout.write(self.style.WARNING("Karar listesi boş veya son sayfa olabilir."))
                break

            index = 0
            while index < len(karar_blocks):
                try:
                    # Her seferinde karar bloklarını yeniden alıyoruz.
                    karar_blocks = driver.find_elements(By.CSS_SELECTOR, "div.birkarar")
                    block = karar_blocks[index]
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"Karar bloğu alınamadı: {e}"))
                    index += 1
                    continue

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
                time.sleep(random.uniform(1, 2))

                try:
                    detail_data = self.extract_detail_data(driver)
                    # Anahtar kelimeler: "BİREYSEL BAŞVURU" ifadesi + (I. BAŞVURUNUN ÖZETİ sonrası ilk paragraf)
                    if detail_data["anahtar_kelime_paragraf"]:
                        anahtar_kelimeler = f"BİREYSEL BAŞVURU ({detail_data['anahtar_kelime_paragraf']})"
                    else:
                        anahtar_kelimeler = "BİREYSEL BAŞVURU"

                    db.connections.close_all()

                    JudicialDecision.objects.create(
                        karar_turu=KARAR_TURU,
                        karar_veren_mahkeme="Anayasa Mahkemesi",
                        esas_numarasi=(detail_data["esas_no"] + " E.") if detail_data["esas_no"] != "Bilinmiyor" else "Bilinmiyor",
                        karar_numarasi=(detail_data["karar_no"] + " K.") if detail_data["karar_no"] != "Bilinmiyor" else "Bilinmiyor",
                        karar_tarihi=detail_data["karar_tarihi"],
                        anahtar_kelimeler=anahtar_kelimeler,
                        # Modeldeki 'karar_ozeti' alanına hüküm özet bilgisi aktarılıyor.
                        karar_ozeti=detail_data["hukum_ozeti"],
                        karar_tam_metni=detail_data["full_text"],
                    )
                    self.stdout.write(self.style.SUCCESS("Karar başarıyla kaydedildi!"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Detay sayfasından veri çekilirken hata: {e}"))

                try:
                    self.click_back(driver)
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"Geri butonuna tıklanırken hata: {e}"))
                    self.stdout.write("Lütfen tarayıcıda geri butonuna veya listeye manuel dönüp Enter'a basın...")
                    input("Devam etmek için Enter'a basınız...")

                time.sleep(random.uniform(1, 2))
                index += 1

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
                continue

        driver.quit()
        self.stdout.write("Tarayıcı kapatıldı, işlem tamamlandı.")
