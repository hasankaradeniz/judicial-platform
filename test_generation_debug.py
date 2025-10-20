#\!/usr/bin/env python
import os
import sys
import django

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'judicial_platform.settings')
django.setup()

from core.legal_text_generator import LegalTextGenerator

# Test generation
generator = LegalTextGenerator()
test_params = {
    'mahkeme': 'İSTANBUL 1. ASLİYE HUKUK MAHKEMESİ',
    'davaci': 'Ali Yılmaz',
    'davali': 'Mehmet Demir',
    'konu': '**Alacak Davası**',
    'alacak_miktari': '50.000',
    'tarih': '01.01.2024',
    'işlem': '**ödünç para** verilmesi',
    'vade': '01.06.2024',
    'talep': 'Ana para ile birlikte işlemiş faizlerin tahsili'
}

result = generator.generate_document('dilekce', {'subtype': 'alacak', **test_params})

print(f"Result keys: {list(result.keys())}")
print(f"Success: {result.get('success')}")
if 'error' in result:
    print(f"Error: {result['error']}")
if 'content' in result:
    print(f"Content length: {len(result['content'])}")
    print(f"Content preview: {result['content'][:200]}")
    print(f"Contains asterisks: {'**' in result['content']}")
else:
    print("No content key found")
