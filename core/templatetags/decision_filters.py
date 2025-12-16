from django import template
from django.utils.safestring import mark_safe
import re

register = template.Library()

@register.filter(name='format_summary')
def format_summary(text):
    if not text:
        return "Özet mevcut değil"
    
    # Simply replace **text** with <strong>text</strong>
    formatted_text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    
    # Convert line breaks to HTML
    formatted_text = formatted_text.replace('\n', '<br>')
    
    return mark_safe(formatted_text)
