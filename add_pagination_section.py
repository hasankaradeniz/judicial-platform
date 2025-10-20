# Pagination HTML ekle
with open('core/templates/core/judicial_decisions.html', 'r') as f:
    content = f.read()

# Pagination HTML
pagination_html = '''
    
    <\!-- Pagination -->
    {% if has_filters and newest_decisions.has_other_pages %}
    <div class="pagination-container">
      <div class="pagination-controls">
        {% if newest_decisions.has_previous %}
          <a href="?{% for key, value in request.GET.items %}{% if key \!= 'page' %}{{ key }}={{ value }}&{% endif %}{% endfor %}page={{ newest_decisions.previous_page_number }}" class="pagination-btn">
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
          <a href="?{% for key, value in request.GET.items %}{% if key \!= 'page' %}{{ key }}={{ value }}&{% endif %}{% endfor %}page={{ newest_decisions.next_page_number }}" class="pagination-btn">
            Sonraki <i class="fas fa-chevron-right"></i>
          </a>
        {% else %}
          <button class="pagination-btn" disabled>
            Sonraki <i class="fas fa-chevron-right"></i>
          </button>
        {% endif %}
      </div>
    </div>
    {% endif %}'''

# latestDecisionsContainer'ın kapanışını bul ve pagination ekle
content = content.replace(
    '</div>\n</div>\n\n<\!-- Latest Decisions (when no search) -->',
    pagination_html + '\n  </div>\n</div>\n\n<\!-- Latest Decisions (when no search) -->'
)

with open('core/templates/core/judicial_decisions.html', 'w') as f:
    f.write(content)

print('Pagination eklendi')
