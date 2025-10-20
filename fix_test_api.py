import re

# Read the file
with open('core/templates/core/legal_text_generator.html', 'r') as f:
    content = f.read()

# Find and replace the test API function
old_pattern = r"""// Test API endpoint function
function testAPIEndpoint\(\) {
    console.log\('=== API Endpoint Testi ==='\);
    
    const testUrl = '/ai/generate-from-multiple-documents/';
    
    // Basit bir GET isteği yaparak endpoint'in var olup olmadığını test et
    fetch\(testUrl, {
        method: 'GET',
        },
        body: new FormData\(\) // Empty FormData for test
        headers: {
            'X-CSRFToken': getCookie\('csrftoken'\)
        }
    }\)"""

new_pattern = """// Test API endpoint function
function testAPIEndpoint() {
    console.log('=== API Endpoint Testi ===');
    
    const testUrl = '/ai/generate-from-multiple-documents/';
    
    // Test POST endpoint
    const formData = new FormData();
    formData.append('document_type', 'test');
    formData.append('additional_instructions', 'API test');
    
    fetch(testUrl, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: formData
    })"""

# Replace
content = content.replace(old_pattern, new_pattern)

# Write back
with open('core/templates/core/legal_text_generator.html', 'w') as f:
    f.write(content)

print('Fixed test API function')
