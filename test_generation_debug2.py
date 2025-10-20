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

print(f"Result: {result}")
if result.get('success') and 'document' in result:
    doc = result['document']
    print(f"\nDocument keys: {list(doc.keys()) if isinstance(doc, dict) else 'Not a dict'}")
    if isinstance(doc, dict) and 'content' in doc:
        content = doc['content']
        print(f"\nContent length: {len(content)}")
        print(f"Content preview: {content[:300]}")
        print(f"Contains asterisks: {'**' in content}")
    else:
        print(f"\nDocument type: {type(doc)}")
        print(f"Document: {doc[:300] if isinstance(doc, str) else doc}")
