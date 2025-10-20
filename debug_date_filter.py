import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'judicial_platform.settings')
import django
django.setup()

from django.test import RequestFactory
from core.views import judicial_decisions
from datetime import datetime

# Test request
rf = RequestFactory()
request = rf.get('/?court_type=YARGITAY&date_range=2020_onwards')
request.session = {}

# Parametreleri kontrol et
print('Request parametreleri:')
for key, value in request.GET.items():
    print(f'{key}: {value}')

# Tarih hesaplama
date_range = 'last_year'
today = datetime.now().date()
print(f'\nBugün: {today}')
print(f'1 yıl önce: {today.replace(year=today.year-1)}')
print(f'2020 tarih: 2020-01-01')
