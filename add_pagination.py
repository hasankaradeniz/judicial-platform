import re

# Template dosyasını oku
with open('core/templates/core/judicial_decisions.html', 'r') as f:
    content = f.read()

# decisions-grid bitiminden sonra pagination ekle
pagination_html = '''
    </div>
    
    <!-- Pagination for filtered results -->
    {% if has_filters and newest_decisions.has_other_pages %}
    <div class="pagination-container">
      <div class="pagination-controls">
        {% if newest_decisions.has_previous %}
          <a href="?{{ request.GET.urlencode }}&page={{ newest_decisions.previous_page_number }}" class="pagination-btn">
            <i class="fas fa-chevron-left"></i> Önceki
          </a>
        {% else %}
          <button class="pagination-btn" disabled>
            <i class="fas fa-chevron-left"></i> Önceki
          </button>
        {% endif %}
        
        <div class="pagination-info">
          Sayfa {{ newest_decisions.number }} / {{ newest_decisions.paginator.num_pages }}
          ({{ newest_decisions.start_index }}-{{ newest_decisions.end_index }} / {{ total_decisions }} sonuç)
        </div>
        
        {% if newest_decisions.has_next %}
          <a href="?{{ request.GET.urlencode }}&page={{ newest_decisions.next_page_number }}" class="pagination-btn">
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
</div>'''

# decisions-grid kapanışını bulup pagination ekle
content = re.sub(
    r'({% endfor %}\s*</div>\s*</div>\s*</div>)',
    '{% endfor %}' + pagination_html,
    content,
    flags=re.DOTALL
)

# Dosyayı yaz
with open('core/templates/core/judicial_decisions.html', 'w') as f:
    f.write(content)

print('✅ Pagination HTML eklendi')
print('✅ Sayfa numaraları çalışacak')