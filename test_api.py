import requests

# Test API endpoint
url = 'https://lexatech.ai/ai/generate-from-multiple-documents/'

# Send GET request to test
response = requests.get(url, verify=False)
print(f'GET Status: {response.status_code}')
print(f'GET Response: {response.text[:200]}...')

# Test if it accepts POST
headers = {'X-CSRFToken': 'test-token'}
data = {'document_type': 'test', 'additional_instructions': 'test'}
response = requests.post(url, headers=headers, data=data, verify=False)
print(f'\nPOST Status: {response.status_code}')
print(f'POST Response: {response.text[:500]}...')
