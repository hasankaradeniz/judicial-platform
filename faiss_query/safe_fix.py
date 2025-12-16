#!/usr/bin/env python3
"""
Safe fix for FAISS views KeyError issue
"""

fix_script = '''
# Read backup views
with open('views.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add simple safety check around the mapping access
content = content.replace(
    'karar_data = mapping[idx]',
    """try:
                    karar_data = mapping[int(idx)]
                except (KeyError, IndexError, TypeError):
                    continue"""
)

# Add ozet field 
content = content.replace(
    "'text': text",
    "'text': text,\\n                'ozet': text[:300] + '...' if len(text) > 300 else text"
)

# Write back
with open('views.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ Added safe mapping access and ozet field')
'''

print("Safe fix script content:")
print(fix_script)