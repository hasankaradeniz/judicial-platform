from django import template
from django.utils.safestring import mark_safe
import re

register = template.Library()

@register.filter
def format_summary(text):
    """Convert ** to line breaks and format for display"""
    if not text:
        return ""
    
    # Replace ** with HTML line breaks
    formatted_text = text.replace('**', '<br><br>')
    
    # Clean up any multiple line breaks
    formatted_text = re.sub(r'<br><br>+', '<br><br>', formatted_text)
    
    # Remove leading/trailing breaks
    formatted_text = formatted_text.strip('<br>')
    
    return mark_safe(formatted_text)
