# core/management/commands/fetch_google_articles.py
from django.core.management.base import BaseCommand
from core.views import google_search  # google_search fonksiyonunu kullanıyoruz
from core.models import Article
import requests
from bs4 import BeautifulSoup


def fetch_full_text(url):
    """
    Belirtilen URL'deki web sayfasının tam metnini, sayfadaki <p> etiketlerinden çıkarır.
    """
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        paragraphs = soup.find_all('p')
        full_text = "\n".join([p.get_text(strip=True) for p in paragraphs])
        return full_text if full_text else "Makale tam metni bulunamadı."
    except Exception as e:
        return "Makale tam metni çekilemedi."


class Command(BaseCommand):
    help = 'Google API kullanarak makaleleri getir ve veritabanına kaydet'

    def add_arguments(self, parser):
        parser.add_argument('query', type=str, help='Aranacak kelime veya ifade')

    def handle(self, *args, **kwargs):
        query = kwargs['query']
        results = google_search(query)
        for item in results:
            title = item.get('title')
            snippet = item.get('snippet')
            link = item.get('link')

            # Makalenin tam metnini çekiyoruz
            full_text = fetch_full_text(link)

            # Makale metni, kaynak linki ve tam metin birleştirilerek oluşturuluyor.
            article_text = f"Kaynak: {link}\n\nTam Metin:\n{full_text}"

            article, created = Article.objects.get_or_create(
                makale_basligi=title,
                defaults={
                    'makale_ozeti': snippet,
                    'makale_metni': article_text,
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Makale eklendi: {title}"))
            else:
                self.stdout.write(f"Makale zaten mevcut: {title}")
