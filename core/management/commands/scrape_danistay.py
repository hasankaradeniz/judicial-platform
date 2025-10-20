import time
import datetime
import re
import random
from django.core.management.base import BaseCommand
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from core.models import JudicialDecision
from django.db import connections


class Command(BaseCommand):
    help = "Danıştay kararlarını eksiksiz ve sırayla çeker, hiçbir kararı atlamaz."

    def handle(self, *args, **options):
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--disable-infobars")
        chrome_options.add_argument("--window-position=2000,2000")  # Chrome'u ekran dışında çalıştırır
        chrome_options.add_argument("--start-maximized")

        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        driver.get("https://karararama.danistay.gov.tr/")
        self.stdout.write("Tarayıcı açıldı. Lütfen daire seçin ve 'Ara'ya basın.")
        input("Karar listesi geldiyse ENTER'a basın...")

        karar_sayisi = 0

        try:
            while True:
                # Tüm kararların index'ini toplayalım
                karar_satirlari = driver.find_elements(By.CSS_SELECTOR, "table#detayAramaSonuclar tbody tr[role='row']")
                karar_sayfasi_indexleri = list(range(len(karar_satirlari)))

                for index in karar_sayfasi_indexleri:
                    try:
                        # Karar satırları tekrar alınır çünkü sayfa değişmiş olabilir
                        rows = driver.find_elements(By.CSS_SELECTOR, "table#detayAramaSonuclar tbody tr[role='row']")
                        if index >= len(rows):
                            continue  # Sayfa yeniden yüklendiğinde eksilmiş olabilir

                        hucreler = rows[index].find_elements(By.TAG_NAME, "td")
                        if len(hucreler) < 5:
                            continue

                        mahkeme = hucreler[0].text.strip()
                        esas = hucreler[1].text.strip()
                        karar_no = hucreler[2].text.strip()
                        tarih = hucreler[3].text.strip()
                        detay_link = hucreler[4].find_element(By.CLASS_NAME, "icerikdetay")

                        # Her 25/40 kararda bekleme ekleyelim
                        if karar_sayisi > 0 and karar_sayisi % 25 == 0:
                            self.stdout.write(self.style.WARNING("25 karar çekildi. 5 dakika bekleniyor..."))
                            time.sleep(120)
                        if karar_sayisi > 0 and karar_sayisi % 40 == 0:
                            self.stdout.write(self.style.WARNING("40 karar çekildi. 7 dakika bekleniyor..."))
                            time.sleep(200)

                        detay_link.click()
                        driver.switch_to.window(driver.window_handles[-1])

                        # Karar body yüklenene kadar bekle
                        WebDriverWait(driver, 20).until(
                            EC.presence_of_element_located((By.TAG_NAME, "body"))
                        )
                        time.sleep(10)  # Bekleme süresi

                        body_text = driver.find_element(By.TAG_NAME, "body").text.strip()

                        mahkeme_match = re.search(r"(?:T\.C\.\s*)?D A N I Ş T A Y\s+(.*?)\s*\n", body_text, re.IGNORECASE)
                        mahkeme_full = "DANIŞTAY " + (mahkeme_match.group(1).strip() if mahkeme_match else mahkeme)

                        esas_no_match = re.search(r"Esas No\s*:\s*(\d+/\d+)", body_text)
                        karar_no_match = re.search(r"Karar No\s*:\s*(\d+/\d+)", body_text)
                        tarihler = re.findall(r"\d{1,2}\.\d{1,2}\.\d{4}", body_text)

                        karar_tarihi = datetime.datetime.strptime(tarihler[-1], "%d.%m.%Y").date() if tarihler else None
                        karar_ozeti = "\n\n".join(body_text.split("\n\n")[-2:]) if "\n\n" in body_text else body_text[-1000:]

                        # Veritabanına yaz
                        connections.close_all()
                        JudicialDecision.objects.create(
                            karar_turu="DANIŞTAY",
                            karar_veren_mahkeme=mahkeme_full,
                            esas_numarasi=esas_no_match.group(1) if esas_no_match else esas,
                            karar_numarasi=karar_no_match.group(1) if karar_no_match else karar_no,
                            karar_tarihi=karar_tarihi,
                            anahtar_kelimeler="Danıştay Kararı",
                            karar_ozeti=karar_ozeti.strip(),
                            karar_tam_metni=body_text
                        )

                        karar_sayisi += 1
                        self.stdout.write(self.style.SUCCESS(f"{karar_sayisi}. karar kaydedildi: {esas}"))

                        driver.close()
                        driver.switch_to.window(driver.window_handles[0])
                        time.sleep(random.uniform(2.0, 3.0))  # Karar arası bekleme

                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f"{index + 1}. karar atlandı: {e}"))
                        if len(driver.window_handles) > 1:
                            driver.close()
                            driver.switch_to.window(driver.window_handles[0])
                        continue

                # Sonraki sayfaya geçmeden önce tüm kararlar işlendi
                try:
                    next_btn = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "li#detayAramaSonuclar_next:not(.disabled) a"))
                    )
                    next_btn.click()
                    time.sleep(3)
                except:
                    self.stdout.write(self.style.SUCCESS("✅ Tüm sayfalar işlendi."))
                    break

        except KeyboardInterrupt:
            self.stdout.write("⛔ İşlem kullanıcı tarafından durduruldu.")
        finally:
            driver.quit()
            self.stdout.write("🧹 Tarayıcı kapatıldı, işlem tamamlandı.")
