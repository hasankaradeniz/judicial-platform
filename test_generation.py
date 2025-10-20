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

if result['success']:
    print("SUCCESS - Generated content:")
    print("="*50)
    print(result['content'][:500])
    print("="*50)
    print(f"\nContent length: {len(result['content'])} characters")
    print(f"Contains asterisks: {'**' in result['content']}")
else:
    print(f"FAILED: {result.get('error')}")
