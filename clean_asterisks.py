import re

def clean_asterisks(text):
    """Metinden yıldız işaretlerini temizle"""
    if not text:
        return text
    
    # Tek ve çift yıldızları temizle
    text = re.sub(r'\*{1,2}([^\*]+)\*{1,2}', r'\1', text)
    
    # Başta ve sonda kalan yıldızları temizle
    text = re.sub(r'^\*+|\*+$', '', text, flags=re.MULTILINE)
    
    # Ardışık yıldızları temizle
    text = re.sub(r'\*{2,}', '', text)
    
    return text.strip()

# Test
if __name__ == '__main__':
    test_text = """**SÖZLEŞME**
    
    **1. TARAFLAR**
    Bu sözleşme *aşağıdaki* taraflar arasında **imzalanmıştır**:
    
    **Kiralayan:** Ali Veli
    **Kiracı:** Ayşe Fatma
    """
    
    print("Önce:")
    print(test_text)
    print("\nSonra:")
    print(clean_asterisks(test_text))
