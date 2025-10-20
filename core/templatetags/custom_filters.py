from django import template
import re

register = template.Library()

@register.filter
def format_summary(value):
    """Format summary text with proper sections"""
    if not value:
        return value
    
    # Replace section headers with formatted versions
    patterns = [
        (r'\*\*1\. DAVA KONUSU:', '<strong>1. DAVA KONUSU:</strong>'),
        (r'\*\*2\. YARGITAY DEĞERLENDİRMESİ:', '<strong>2. YARGITAY DEĞERLENDİRMESİ:</strong>'),
        (r'\*\*3\. SONUÇ:', '<strong>3. SONUÇ:</strong>'),
        (r'\*\*([0-9]+)\.\s*([A-ZÇĞİÖŞÜ\s]+):', r'<strong>\1. \2:</strong>'),
    ]
    
    formatted = value
    for pattern, replacement in patterns:
        formatted = re.sub(pattern, replacement, formatted)
    
    # Convert line breaks to paragraphs
    paragraphs = formatted.split('\n\n')
    formatted_paragraphs = []
    
    for p in paragraphs:
        p = p.strip()
        if p:
            if p.startswith('<strong>'):
                formatted_paragraphs.append(p)
            else:
                formatted_paragraphs.append(f'<p>{p}</p>')
    
    return '\n'.join(formatted_paragraphs)

@register.filter
def format_decision_text(value):
    """Format decision full text for better readability"""
    if not value:
        return value
    
    # Clean up the text first
    text = value.strip()
    
    # Detect format type
    has_yargitay_header = 'Y A R G I T A Y' in text or 'YARGITAY KARARI' in text
    has_karar_section = '-KARAR-' in text
    has_danistay = 'DANIŞTAY' in text or 'Danıştay' in text
    has_tetkik_hakimi = 'TETKİK HAKİMİ' in text or 'DÜŞÜNCESİ' in text
    
    if has_danistay or has_tetkik_hakimi:
        # Danıştay format (Format 3)
        return format_danistay_decision(text)
    elif has_karar_section and not has_yargitay_header:
        # Simple format (Format 2)
        return format_simple_decision(text)
    else:
        # Detailed format (Format 1)
        return format_detailed_decision(text)

def format_danistay_decision(text):
    """Format Danıştay decision style with Tetkik Hakimi sections"""
    patterns = [
        # Court header
        (r'^([A-ZÇĞİÖŞÜa-zçğıöşü\s]+\s+Dairesi)\s+(\d{4}/\d+\s*E\.\s*,\s*\d{4}/\d+\s*K\.)', 
         r'<div class="court-header-text"><strong>\1</strong><span class="case-numbers">\2</span></div>'),
        
        # Main title
        (r'"İçtihat Metni"', '<div class="decision-title">"İçtihat Metni"</div>'),
        
        # Info fields
        (r'MAHKEMESİ\s*:\s*(.+?)(?=\n|$)', r'<div class="info-row"><span class="info-label">MAHKEMESİ</span><span class="info-value">\1</span></div>'),
        (r'DAVA TÜRÜ\s*:\s*(.+?)(?=\n|$)', r'<div class="info-row"><span class="info-label">DAVA TÜRÜ</span><span class="info-value">\1</span></div>'),
        
        # Danıştay specific headers
        (r'(\n|^)(DANIŞTAY TETKİK HAKİMİ\s+[^\']+\'[ÜU]N DÜŞÜNCESİ:)\s*(\n|$)', r'\n<div class="section-header">\2</div>\n'),
        (r'(\n|^)(DANIŞTAY SAVCISI\s+[^\']+\'[ÜU]N DÜŞÜNCESİ:)\s*(\n|$)', r'\n<div class="section-header">\2</div>\n'),
        
        # Standard section headers
        (r'(\n|^)(Davacı İsteminin Özeti:)\s*(\n|$)', r'\n<div class="section-header">\2</div>\n'),
        (r'(\n|^)(Davalı Cevabının Özeti:)\s*(\n|$)', r'\n<div class="section-header">\2</div>\n'),
        (r'(\n|^)(Mahkeme Kararının Özeti:)\s*(\n|$)', r'\n<div class="section-header">\2</div>\n'),
        (r'(\n|^)(Temyiz:)\s*(\n|$)', r'\n<div class="section-header">\2</div>\n'),
        (r'(\n|^)(Gerekçe:)\s*(\n|$)', r'\n<div class="section-header">\2</div>\n'),
        (r'(\n|^)(TÜRK MİLLETİ ADINA)\s*(\n|$)', r'\n<div class="section-header-special">\2</div>\n'),
        (r'(\n|^)(SONUÇ:)(\s*)', r'\n<div class="section-header-conclusion">\2</div>\n'),
        
        # Legal references
        (r'(\d+\.\s*madde(?:si)?)', r'<span class="legal-ref">\1</span>'),
        (r'(\d+/\d+\.\s*madde(?:si)?)', r'<span class="legal-ref">\1</span>'),
        (r'(\d+\s*sayılı\s*[^.]+\s*Kanun)', r'<span class="legal-ref">\1</span>'),
        
        # Money amounts
        (r'(\d+(?:\.\d{3})*(?:,\d{2})?\s*TL\.?)', r'<span class="money-ref">\1</span>'),
    ]
    
    # Apply patterns
    formatted = text
    for pattern, replacement in patterns:
        formatted = re.sub(pattern, replacement, formatted, flags=re.MULTILINE | re.IGNORECASE)
    
    # Convert to paragraphs with proper spacing
    lines = formatted.split('\n')
    result_lines = []
    in_paragraph = False
    paragraph_buffer = []
    
    for i, line in enumerate(lines):
        line = line.strip()
        
        # Empty line indicates paragraph break
        if not line:
            if paragraph_buffer:
                # Close current paragraph
                result_lines.append('<p class="danistay-paragraph">' + ' '.join(paragraph_buffer) + '</p>')
                result_lines.append('<div class="paragraph-spacer"></div>')  # Visual spacer
                paragraph_buffer = []
            continue
        
        # Check if line contains HTML tags (headers, etc.)
        if any(tag in line for tag in ['<div', '<span', '</div>', '</span>']):
            # Flush any buffered paragraph content
            if paragraph_buffer:
                result_lines.append('<p class="danistay-paragraph">' + ' '.join(paragraph_buffer) + '</p>')
                result_lines.append('<div class="paragraph-spacer"></div>')
                paragraph_buffer = []
            result_lines.append(line)
        else:
            # Check if this is a new sentence that should start a new paragraph
            if paragraph_buffer and line[0].isupper() and paragraph_buffer[-1].endswith('.'):
                # End current paragraph and start new one
                result_lines.append('<p class="danistay-paragraph">' + ' '.join(paragraph_buffer) + '</p>')
                result_lines.append('<div class="paragraph-spacer"></div>')
                paragraph_buffer = [line]
            else:
                # Add to current paragraph
                paragraph_buffer.append(line)
    
    # Don't forget the last paragraph
    if paragraph_buffer:
        result_lines.append('<p class="danistay-paragraph">' + ' '.join(paragraph_buffer) + '</p>')
    
    return '\n'.join(result_lines)

def format_simple_decision(text):
    """Format simple decision style without subsection headers"""
    patterns = [
        # Court header
        (r'^([A-ZÇĞİÖŞÜa-zçğıöşü\s]+\s+Dairesi)\s+(\d{4}/\d+\s*E\.\s*,\s*\d{4}/\d+\s*K\.)', 
         r'<div class="court-header-text"><strong>\1</strong><span class="case-numbers">\2</span></div>'),
        
        # Main title
        (r'"İçtihat Metni"', '<div class="decision-title">"İçtihat Metni"</div>'),
        
        # Info fields
        (r'MAHKEMESİ\s*:\s*(.+?)(?=\n|$)', r'<div class="info-row"><span class="info-label">MAHKEMESİ</span><span class="info-value">\1</span></div>'),
        (r'DAVA TÜRÜ\s*:\s*(.+?)(?=\n|$)', r'<div class="info-row"><span class="info-label">DAVA TÜRÜ</span><span class="info-value">\1</span></div>'),
        
        # KARAR section header - centered and bold with spacing
        (r'(\n|^)(-KARAR-)\s*(\n|$)', r'\n<br><div class="karar-header-center"><strong>\2</strong></div><br>\n'),
        
        # Legal references
        (r'(\d+\.\s*madde(?:si)?)', r'<span class="legal-ref">\1</span>'),
        (r'(\d+/\d+\.\s*madde(?:si)?)', r'<span class="legal-ref">\1</span>'),
        (r'(\d+\s*sayılı\s*[^.]+\s*Kanun)', r'<span class="legal-ref">\1</span>'),
        
        # Money amounts
        (r'(\d+(?:\.\d{3})*(?:,\d{2})?\s*TL\.?)', r'<span class="money-ref">\1</span>'),
    ]
    
    # Apply patterns
    formatted = text
    for pattern, replacement in patterns:
        formatted = re.sub(pattern, replacement, formatted, flags=re.MULTILINE | re.IGNORECASE)
    
    # Convert to paragraphs with proper spacing
    lines = formatted.split('\n')
    result_lines = []
    paragraph_buffer = []
    
    for line in lines:
        line = line.strip()
        
        # Empty line indicates paragraph break
        if not line:
            if paragraph_buffer:
                # Close current paragraph
                result_lines.append('<p class="paragraph-indent">' + ' '.join(paragraph_buffer) + '</p>')
                result_lines.append('<div class="paragraph-spacer"></div>')  # Visual spacer
                paragraph_buffer = []
            continue
        
        # Check if line contains HTML tags
        if any(tag in line for tag in ['<div', '<span', '</div>', '</span>']):
            # Flush any buffered paragraph content
            if paragraph_buffer:
                result_lines.append('<p class="paragraph-indent">' + ' '.join(paragraph_buffer) + '</p>')
                result_lines.append('<div class="paragraph-spacer"></div>')
                paragraph_buffer = []
            result_lines.append(line)
        else:
            # Check if this is a new sentence that should start a new paragraph
            if paragraph_buffer and line[0].isupper() and paragraph_buffer[-1].endswith('.'):
                # End current paragraph and start new one
                result_lines.append('<p class="paragraph-indent">' + ' '.join(paragraph_buffer) + '</p>')
                result_lines.append('<div class="paragraph-spacer"></div>')
                paragraph_buffer = [line]
            else:
                # Add to current paragraph
                paragraph_buffer.append(line)
    
    # Don't forget the last paragraph
    if paragraph_buffer:
        result_lines.append('<p class="paragraph-indent">' + ' '.join(paragraph_buffer) + '</p>')
    
    return '\n'.join(result_lines)

def format_detailed_decision(text):
    """Format detailed decision style with subsection headers"""
    patterns = [
        # Court header
        (r'^([A-ZÇĞİÖŞÜa-zçğıöşü\s]+\s+Dairesi)\s+(\d{4}/\d+\s*E\.\s*,\s*\d{4}/\d+\s*K\.)', 
         r'<div class="court-header-text"><strong>\1</strong><span class="case-numbers">\2</span></div>'),
        
        # Main title
        (r'"İçtihat Metni"', '<div class="decision-title">"İçtihat Metni"</div>'),
        
        # Info fields
        (r'MAHKEMESİ\s*:\s*(.+?)(?=\n|$)', r'<div class="info-row"><span class="info-label">MAHKEMESİ</span><span class="info-value">\1</span></div>'),
        (r'İHBAR OLUNAN\s*:\s*(.+?)(?=\n|$)', r'<div class="info-row"><span class="info-label">İHBAR OLUNAN</span><span class="info-value">\1</span></div>'),
        (r'DAVA TÜRÜ\s*:\s*(.+?)(?=\n|$)', r'<div class="info-row"><span class="info-label">DAVA TÜRÜ</span><span class="info-value">\1</span></div>'),
        
        # Section headers
        (r'\n(Y\s*A\s*R\s*G\s*I\s*T\s*A\s*Y\s+K\s*A\s*R\s*A\s*R\s*I)\s*\n', r'\n<div class="main-section-header">\1</div>\n'),
        
        # Subsection headers
        (r'(\n|^)(Davacı İsteminin Özeti:)\s*(\n|$)', r'\n<div class="section-header">\2</div>\n'),
        (r'(\n|^)(Davalı Cevabının Özeti:)\s*(\n|$)', r'\n<div class="section-header">\2</div>\n'),
        (r'(\n|^)(Mahkeme Kararının Özeti:)\s*(\n|$)', r'\n<div class="section-header">\2</div>\n'),
        (r'(\n|^)(Temyiz:)\s*(\n|$)', r'\n<div class="section-header">\2</div>\n'),
        (r'(\n|^)(Gerekçe:)\s*(\n|$)', r'\n<div class="section-header">\2</div>\n'),
        (r'(\n|^)(SONUÇ:)(\s*)', r'\n<div class="section-header-conclusion">\2</div>\n'),
        
        # Legal references
        (r'(\d+\.\s*madde(?:si)?)', r'<span class="legal-ref">\1</span>'),
        (r'(\d+/\d+\s*madde(?:si)?)', r'<span class="legal-ref">\1</span>'),
        (r'(\d+\s*sayılı\s*kanun)', r'<span class="legal-ref">\1</span>'),
        (r'(Yargıtay\s+\([^)]+\)\s+\d+\.\s+[A-ZÇĞİÖŞÜ\s]+Daire)', r'<span class="court-ref">\1</span>'),
        (r'(\d+\.\d+\.\d{4}\s+tarihli\s+(?:bozma\s+)?ilam)', r'<span class="court-ref">\1</span>'),
    ]
    
    # Apply patterns
    formatted = text
    for pattern, replacement in patterns:
        formatted = re.sub(pattern, replacement, formatted, flags=re.MULTILINE | re.IGNORECASE)
    
    # Convert to paragraphs
    lines = formatted.split('\n')
    result_lines = []
    in_paragraph = False
    in_conclusion = False
    
    for i, line in enumerate(lines):
        line = line.strip()
        
        if not line:
            if in_paragraph:
                result_lines.append('</p>')
                in_paragraph = False
            continue
        
        if 'class="section-header-conclusion"' in line:
            in_conclusion = True
            if in_paragraph:
                result_lines.append('</p>')
                in_paragraph = False
            result_lines.append(line)
            continue
        
        if 'class="section-header"' in line:
            in_conclusion = False
        
        if any(tag in line for tag in ['<div', '<span', '</div>', '</span>']):
            if in_paragraph:
                result_lines.append('</p>')
                in_paragraph = False
            result_lines.append(line)
            continue
        
        numbered_match = re.match(r'^(\d+[-\)]\s*)', line)
        if numbered_match:
            if in_paragraph:
                result_lines.append('</p>')
                in_paragraph = False
            
            numbered_part = numbered_match.group(1)
            rest_of_line = line[len(numbered_part):].strip()
            result_lines.append(f'<p><span class="numbered-item">{numbered_part}</span>{rest_of_line}')
            in_paragraph = True
            continue
        
        if in_conclusion:
            if not any(tag in line for tag in ['<div', '</div>']):
                sentences = re.split(r'([.!?]\s+)(?=[A-ZÇĞIÖŞÜ])', line)
                for j in range(0, len(sentences), 2):
                    sentence = sentences[j].strip()
                    if sentence:
                        if j + 1 < len(sentences):
                            sentence += sentences[j + 1]
                        result_lines.append(f'<p class="conclusion-paragraph">{sentence}</p>')
            else:
                result_lines.append(line)
        else:
            if not in_paragraph:
                result_lines.append('<p>')
                in_paragraph = True
            result_lines.append(line)
    
    if in_paragraph:
        result_lines.append('</p>')
    
    return '\n'.join(result_lines)

@register.filter  
def split(value, delimiter):
    """Split a string by delimiter"""
    return value.split(delimiter) if value else []

@register.filter
def trim(value):
    """Trim whitespace from string"""
    return value.strip() if value else ''