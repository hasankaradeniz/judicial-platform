import sys
sys.path.append('/var/www/judicial_platform')
from core.legal_text_generator import LegalTextGenerator

gen = LegalTextGenerator()
test_text = '**Bu bir test** metnidir. *İtalik metin* ve normal metin.'
cleaned = gen.clean_markdown_formatting(test_text)
print(f'Original: {test_text}')
print(f'Cleaned: {cleaned}')
