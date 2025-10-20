#\!/usr/bin/env python3
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'judicial_platform.settings')
django.setup()

from django.test import RequestFactory
from core.views import judicial_decisions

# Test request oluştur
rf = RequestFactory()
request = rf.get('/judicial-decisions/?court_type=yargitay&case_number=2023')
request.session = {}

# View'e gelen parametreleri göster
print("GET parametreleri:")
print(f"query: '{request.GET.get('q', '')}'")
print(f"court_type: '{request.GET.get('court_type', '')}'")
print(f"case_number: '{request.GET.get('case_number', '')}'")
print(f"decision_number: '{request.GET.get('decision_number', '')}'")

# has_any_filter kontrolü
query = request.GET.get('q', '').strip()
court_type = request.GET.get('court_type', '').strip()
case_number = request.GET.get('case_number', '').strip()
decision_number = request.GET.get('decision_number', '').strip()
date_from = request.GET.get('date_from', '').strip()
date_to = request.GET.get('date_to', '').strip()

has_any_filter = any([query, court_type, case_number, decision_number, date_from, date_to])
print(f"\nhas_any_filter: {has_any_filter}")
print(f"Filtreleme yapılacak mı: {'EVET' if has_any_filter else 'HAYIR'}")
