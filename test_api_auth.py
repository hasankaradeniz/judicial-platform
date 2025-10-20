from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.ai_views import generate_from_multiple_documents
from django.test import RequestFactory
from django.core.files.uploadedfile import SimpleUploadedFile
import json

# Create a test request
factory = RequestFactory()
User = get_user_model()

# Get or create a test user
user, created = User.objects.get_or_create(username='test_user', defaults={'email': 'test@example.com'})
if created:
    user.set_password('testpass123')
    user.save()

# Create request with file
content = b'Test PDF content'
uploaded_file = SimpleUploadedFile('test.pdf', content, content_type='application/pdf')

request = factory.post('/ai/generate-from-multiple-documents/', {
    'document_type': 'İstinaf dilekçesi',
    'additional_instructions': 'Test talebi',
    'file_count': '1'
})
request.user = user
request._files = {'source_documents': [uploaded_file]}

# Call the view
try:
    response = generate_from_multiple_documents(request)
    print(f'Status: {response.status_code}')
    if hasattr(response, 'content'):
        print(f'Response: {response.content.decode()}')
except Exception as e:
    print(f'Error: {str(e)}')
    import traceback
    traceback.print_exc()
