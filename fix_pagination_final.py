# Template'i düzelt
with open('core/templates/core/judicial_decisions.html', 'r') as f:
    content = f.read()

# Mevcut pagination container'ı bul
if 'Django Pagination' not in content:
    # decisions-grid'in bitişini bul ve pagination ekle
    
    # Önce {% endfor %} sayısını kontrol et
    endfor_count = content.count('{% endfor %}')
    print(f'Template\'de {endfor_count} adet endfor var')
    
    # En son decision card döngüsünün bitişini bul
    import re
    
    # Pattern: decision cards döngüsünün sonu
    pattern = r'({% endfor %}\s*</div>\s*</div>\s*</div>\s*<!-- Latest Decisions)'
    
    replacement = '''{% endfor %}
    </div>
    
    <!-- Django Pagination -->
    {% if has_filters and is_paginated %}
    <div class="pagination-container" style="display: block !important; margin-top: 30px;">
      <div class="pagination-controls">
        {% if newest_decisions.has_previous %}
          <a href="?{% for key, value in request.GET.items %}{% if key != 'page' %}{{ key }}={{ value }}&{% endif %}{% endfor %}page={{ newest_decisions.previous_page_number }}" class="pagination-btn">
            <i class="fas fa-chevron-left"></i> Önceki
          </a>
        {% else %}
          <button class="pagination-btn" disabled>
            <i class="fas fa-chevron-left"></i> Önceki
          </button>
        {% endif %}
        
        <div class="pagination-info">
          Sayfa {{ newest_decisions.number }} / {{ newest_decisions.paginator.num_pages }}
        </div>
        
        {% if newest_decisions.has_next %}
          <a href="?{% for key, value in request.GET.items %}{% if key != 'page' %}{{ key }}={{ value }}&{% endif %}{% endfor %}page={{ newest_decisions.next_page_number }}" class="pagination-btn">
            Sonraki <i class="fas fa-chevron-right"></i>
          </a>
        {% else %}
          <button class="pagination-btn" disabled>
            Sonraki <i class="fas fa-chevron-right"></i>
          </button>
        {% endif %}
      </div>
    </div>
    {% endif %}
    
  </div>
</div>

<!-- Latest Decisions'''
    
    if re.search(pattern, content):
        content = re.sub(pattern, replacement, content)
        print('✅ Pagination başarıyla eklendi')
    else:
        print('❌ Pattern bulunamadı, alternatif yöntem deneniyor...')
        
        # Alternatif: en son {% endfor %}'dan önce ekle
        last_endfor = content.rfind('{% endfor %}')
        if last_endfor > 0:
            # Bu endfor'dan sonraki </div>'leri say
            after_endfor = content[last_endfor:last_endfor+200]
            div_count = after_endfor.count('</div>')
            print(f'Son endfor\'dan sonra {div_count} adet </div> var')

with open('core/templates/core/judicial_decisions.html', 'w') as f:
    f.write(content)

print('Template güncellendi')