# Professional pagination tasarımı
with open('core/templates/core/judicial_decisions.html', 'r') as f:
    content = f.read()

# Mevcut basit pagination'ı bul ve değiştir
import re

# Yeni profesyonel pagination HTML
professional_pagination = '''
    <!-- Professional Pagination -->
    {% if has_filters and is_paginated %}
    <div class="pagination-wrapper">
      <div class="pagination-container-pro">
        <div class="pagination-info-top">
          <span class="result-summary">
            <i class="fas fa-file-alt"></i>
            Toplam <strong>{{ total_decisions|floatformat:0 }}</strong> sonuç bulundu
          </span>
          <span class="page-info">
            Gösterilen: <strong>{{ newest_decisions.start_index }}-{{ newest_decisions.end_index }}</strong>
          </span>
        </div>
        
        <div class="pagination-controls-pro">
          <!-- İlk Sayfa -->
          {% if newest_decisions.number > 2 %}
            <a href="?{% for key, value in request.GET.items %}{% if key != 'page' %}{{ key }}={{ value }}&{% endif %}{% endfor %}page=1" 
               class="page-btn first-page" title="İlk Sayfa">
              <i class="fas fa-angle-double-left"></i>
            </a>
          {% endif %}
          
          <!-- Önceki -->
          {% if newest_decisions.has_previous %}
            <a href="?{% for key, value in request.GET.items %}{% if key != 'page' %}{{ key }}={{ value }}&{% endif %}{% endfor %}page={{ newest_decisions.previous_page_number }}" 
               class="page-btn prev-page">
              <i class="fas fa-angle-left"></i>
              <span class="btn-text">Önceki</span>
            </a>
          {% endif %}
          
          <!-- Sayfa Numaraları -->
          <div class="page-numbers">
            {% if newest_decisions.number > 3 %}
              <span class="page-dots">...</span>
            {% endif %}
            
            {% for page_num in newest_decisions.paginator.page_range %}
              {% if page_num >= newest_decisions.number|add:"-2" and page_num <= newest_decisions.number|add:"2" %}
                {% if page_num == newest_decisions.number %}
                  <span class="page-num active">{{ page_num }}</span>
                {% else %}
                  <a href="?{% for key, value in request.GET.items %}{% if key != 'page' %}{{ key }}={{ value }}&{% endif %}{% endfor %}page={{ page_num }}" 
                     class="page-num">{{ page_num }}</a>
                {% endif %}
              {% endif %}
            {% endfor %}
            
            {% if newest_decisions.number < newest_decisions.paginator.num_pages|add:"-2" %}
              <span class="page-dots">...</span>
            {% endif %}
          </div>
          
          <!-- Sonraki -->
          {% if newest_decisions.has_next %}
            <a href="?{% for key, value in request.GET.items %}{% if key != 'page' %}{{ key }}={{ value }}&{% endif %}{% endfor %}page={{ newest_decisions.next_page_number }}" 
               class="page-btn next-page">
              <span class="btn-text">Sonraki</span>
              <i class="fas fa-angle-right"></i>
            </a>
          {% endif %}
          
          <!-- Son Sayfa -->
          {% if newest_decisions.number < newest_decisions.paginator.num_pages|add:"-1" %}
            <a href="?{% for key, value in request.GET.items %}{% if key != 'page' %}{{ key }}={{ value }}&{% endif %}{% endfor %}page={{ newest_decisions.paginator.num_pages }}" 
               class="page-btn last-page" title="Son Sayfa">
              <i class="fas fa-angle-double-right"></i>
            </a>
          {% endif %}
        </div>
        
        <!-- Sayfa Atlama -->
        <div class="page-jump">
          <span>Sayfaya git:</span>
          <input type="number" min="1" max="{{ newest_decisions.paginator.num_pages }}" 
                 value="{{ newest_decisions.number }}" class="page-input" id="pageJumpInput">
          <button onclick="jumpToPage()" class="jump-btn">
            <i class="fas fa-arrow-right"></i>
          </button>
        </div>
      </div>
    </div>
    {% endif %}'''

# CSS ekle
pagination_css = '''
<style>
  /* Professional Pagination Styles */
  .pagination-wrapper {
    margin: 40px 0;
    background: linear-gradient(to bottom, #f8f9fa, #fff);
    border-top: 1px solid #e0e0e0;
    padding: 30px 0;
  }
  
  .pagination-container-pro {
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 20px;
  }
  
  .pagination-info-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
    color: #666;
    font-size: 14px;
  }
  
  .result-summary strong, .page-info strong {
    color: #333;
    font-weight: 600;
  }
  
  .pagination-controls-pro {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    margin-bottom: 20px;
  }
  
  .page-btn, .page-num {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 40px;
    height: 40px;
    padding: 0 15px;
    background: #fff;
    border: 1px solid #ddd;
    border-radius: 6px;
    color: #333;
    text-decoration: none;
    font-size: 14px;
    font-weight: 500;
    transition: all 0.2s ease;
    cursor: pointer;
  }
  
  .page-btn:hover, .page-num:hover {
    background: #007bff;
    color: white;
    border-color: #007bff;
    transform: translateY(-1px);
    box-shadow: 0 2px 8px rgba(0, 123, 255, 0.2);
  }
  
  .page-num.active {
    background: #007bff;
    color: white;
    border-color: #007bff;
    font-weight: 600;
    cursor: default;
  }
  
  .page-num.active:hover {
    transform: none;
  }
  
  .page-btn.first-page, .page-btn.last-page {
    min-width: 40px;
    padding: 0;
  }
  
  .page-btn .btn-text {
    margin: 0 5px;
  }
  
  .page-numbers {
    display: flex;
    align-items: center;
    gap: 4px;
  }
  
  .page-dots {
    color: #999;
    padding: 0 8px;
    font-weight: 500;
  }
  
  .page-jump {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    color: #666;
    font-size: 14px;
  }
  
  .page-input {
    width: 60px;
    height: 36px;
    padding: 0 10px;
    border: 1px solid #ddd;
    border-radius: 4px;
    text-align: center;
    font-size: 14px;
  }
  
  .jump-btn {
    width: 36px;
    height: 36px;
    background: #007bff;
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    transition: all 0.2s ease;
  }
  
  .jump-btn:hover {
    background: #0056b3;
    transform: translateY(-1px);
  }
  
  /* Responsive */
  @media (max-width: 768px) {
    .pagination-info-top {
      flex-direction: column;
      gap: 10px;
      text-align: center;
    }
    
    .pagination-controls-pro {
      flex-wrap: wrap;
    }
    
    .page-btn .btn-text {
      display: none;
    }
    
    .page-jump {
      margin-top: 15px;
    }
  }
</style>

<script>
function jumpToPage() {
    const input = document.getElementById('pageJumpInput');
    const page = parseInt(input.value);
    const maxPage = parseInt(input.max);
    
    if (page >= 1 && page <= maxPage) {
        const url = new URL(window.location.href);
        url.searchParams.set('page', page);
        window.location.href = url.toString();
    } else {
        alert('Geçersiz sayfa numarası!');
    }
}

// Enter tuşu ile sayfa atlama
document.addEventListener('DOMContentLoaded', function() {
    const pageInput = document.getElementById('pageJumpInput');
    if (pageInput) {
        pageInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                jumpToPage();
            }
        });
    }
});
</script>
'''

# Eski pagination'ı bul ve değiştir
# Önce mevcut basit pagination'ı kaldır
pattern = r'<!-- Django Pagination -->.*?{% endif %}'
content = re.sub(pattern, professional_pagination, content, flags=re.DOTALL)

# CSS'i head tag'ine ekle
if '</head>' in content and 'Professional Pagination Styles' not in content:
    content = content.replace('</head>', pagination_css + '\n</head>')

with open('core/templates/core/judicial_decisions.html', 'w') as f:
    f.write(content)

print('✅ Profesyonel pagination tasarımı uygulandı!')
print('✅ Sayfa numaraları, ilk/son sayfa butonları eklendi')
print('✅ Sayfa atlama özelliği eklendi')
print('✅ Responsive tasarım uygulandı')