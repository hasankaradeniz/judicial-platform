#\!/usr/bin/env python
import os
import sys
import django
import json

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'judicial_platform.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth.models import User
from django.contrib.sessions.middleware import SessionMiddleware
from core.ai_views import generate_legal_text

# Create a test request
factory = RequestFactory()
test_data = {
    'template_type': 'dilekce',
    'parameters': {
        'subtype': 'alacak',
        'mahkeme': 'İSTANBUL 1. ASLİYE HUKUK MAHKEMESİ',
        'davaci': 'Ali Yılmaz',
        'davali': 'Mehmet **Demir**',
        'konu': '**Alacak Davası**',
        'alacak_miktari': '50.000',
        'tarih': '01.01.2024',
        'işlem': '**ödünç para** verilmesi',
        'vade': '01.06.2024',
        'talep': 'Ana para ile birlikte işlemiş **faizlerin** tahsili'
    }
}

request = factory.post('/ai/generate-text/', 
                      data=json.dumps(test_data),
                      content_type='application/json')

# Add session support
middleware = SessionMiddleware(get_response=lambda r: None)
middleware.process_request(request)
request.session.save()

# Create a test user
request.user = User.objects.first() or User.objects.create_user('testuser', 'test@test.com', 'password')

# Call the view
response = generate_legal_text(request)

print(f"Status Code: {response.status_code}")
response_data = json.loads(response.content)
print(f"Success: {response_data.get('success')}")
if response_data.get('success'):
    content = response_data.get('content', '')
    print(f"Content length: {len(content)}")
    print(f"Contains asterisks: {'**' in content}")
    print(f"Session has document: {'last_generated_document' in request.session}")
    if 'last_generated_document' in request.session:
        session_content = request.session['last_generated_document']
        print(f"Session content length: {len(session_content)}")
        print(f"Session content matches response: {content == session_content}")
    print("\nFirst 300 characters:")
    print(content[:300])
else:
    print(f"Error: {response_data.get('error')}")
