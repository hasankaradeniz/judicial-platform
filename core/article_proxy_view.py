# core/article_proxy_view.py

import requests
import time
from bs4 import BeautifulSoup
from django.http import HttpResponse, Http404
from django.shortcuts import render
from urllib.parse import urljoin, urlparse
import re


def article_proxy_view(request, source, article_id):
    """Makale sayfasını proxy ederek tüm linkleri yeni sekmede açacak şekilde düzenle"""
    
    # Session'dan makale bilgilerini al
    session_key = f'article_{article_id}'
    article = request.session.get(session_key)
    
    if not article:
        raise Http404("Makale bulunamadı")
    
    original_url = article.get('detail_link')
    article_title = article.get('title', 'Academic Article')
    
    if not original_url:
        raise Http404("Makale linki bulunamadı")
    
    try:
        print(f"🌐 Makale sayfası proxy ediliyor: {original_url}")
        
        # HTTP session oluştur
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'tr-TR,tr;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        # Sayfayı indir
        response = session.get(original_url, timeout=15)
        
        if response.status_code == 200:
            # HTML içeriğini parse et
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Base URL'i belirle
            base_url = f"{urlparse(original_url).scheme}://{urlparse(original_url).netloc}"
            
            # Base tag ekle (relative URL'ler için)
            add_base_tag(soup, base_url)
            
            # Tüm linkleri düzenle
            modify_links(soup, base_url, original_url)
            
            # CSS ve JS dosyalarını düzenle
            fix_resources(soup, base_url)
            
            # Problematik script'leri devre dışı bırak
            disable_problematic_scripts(soup)
            
            # Custom CSS ve JS ekle
            add_custom_scripts(soup)
            
            # Sayfa başlığını güncelle
            if soup.title:
                soup.title.string = f"{article_title} - Proxy View"
            
            print("✅ Makale sayfası başarıyla proxy edildi")
            
            # Düzenlenmiş HTML'i döndür
            response = HttpResponse(str(soup), content_type='text/html; charset=utf-8')
            response['Cache-Control'] = 'no-cache'
            response['X-Frame-Options'] = 'SAMEORIGIN'
            return response
            
        else:
            print(f"❌ HTTP hatası: {response.status_code}")
            return create_error_response(original_url, article_title, f"HTTP {response.status_code}")
            
    except requests.exceptions.Timeout:
        print("⏰ Timeout hatası")
        return create_error_response(original_url, article_title, "Timeout")
    except requests.exceptions.RequestException as e:
        print(f"🌐 Ağ hatası: {e}")
        return create_error_response(original_url, article_title, "Network Error")
    except Exception as e:
        print(f"❌ Genel hata: {e}")
        return create_error_response(original_url, article_title, "General Error")


def add_base_tag(soup, base_url):
    """Base tag ekle - relative URL'lerin doğru çözümlenmesi için"""
    if soup.head:
        # Mevcut base tag'i kaldır
        existing_base = soup.head.find('base')
        if existing_base:
            existing_base.decompose()
        
        # Yeni base tag ekle
        base_tag = soup.new_tag('base', href=base_url + '/')
        soup.head.insert(0, base_tag)
        print(f"✅ Base tag eklendi: {base_url}/")


def modify_links(soup, base_url, original_url):
    """Tüm linkleri yeni sekmede açacak şekilde düzenle"""
    
    # Tüm a tag'lerini bul
    for link in soup.find_all('a', href=True):
        href = link.get('href')
        
        # Boş veya javascript linkleri atla
        if not href or href.startswith('javascript:') or href.startswith('#'):
            continue
            
        # Relative URL'leri absolute yap
        if href.startswith('//'):
            full_url = f"https:{href}"
        elif href.startswith('/'):
            full_url = base_url + href
        elif not href.startswith('http'):
            full_url = urljoin(original_url, href)
        else:
            full_url = href
        
        # Target ve rel attributelerini ekle
        link['target'] = '_blank'
        link['rel'] = 'noopener noreferrer'
        link['href'] = full_url
        
        # CSS class ekle
        existing_class = link.get('class', [])
        if isinstance(existing_class, str):
            existing_class = [existing_class]
        existing_class.append('proxy-external-link')
        link['class'] = existing_class


def disable_problematic_scripts(soup):
    """Problematik JavaScript kodlarını yumuşak şekilde devre dışı bırak"""
    
    # Sadece çok problematik olan script'leri wrap et
    for script in soup.find_all('script'):
        if script.string:
            script_content = script.string
            
            # Sadece storage erişimi olan script'leri wrap et
            if ('document.cookie' in script_content or 
                'sessionStorage' in script_content or 
                'localStorage' in script_content):
                
                print(f"🚫 Storage access script wrap edildi")
                wrapped_content = f"""
                try {{
                    {script_content}
                }} catch(e) {{
                    console.log('Proxy view: Script error handled', e.message);
                }}
                """
                script.string = wrapped_content
    
    # Sadece problematik inline event handler'ları kaldır
    for element in soup.find_all(attrs=True):
        for attr in list(element.attrs.keys()):
            if attr in ['onclick'] and element.attrs[attr] and 'cookie' in element.attrs[attr].lower():
                print(f"🚫 Problematik inline event handler kaldırıldı: {attr}")
                del element.attrs[attr]


def fix_resources(soup, base_url):
    """CSS, JS ve resim dosyalarının URL'lerini düzelt"""
    
    # CSS dosyaları
    for link in soup.find_all('link', rel='stylesheet'):
        href = link.get('href')
        if href and not href.startswith('http'):
            if href.startswith('//'):
                link['href'] = f"https:{href}"
            elif href.startswith('/'):
                link['href'] = base_url + href
            else:
                link['href'] = urljoin(base_url, href)
    
    # JavaScript dosyaları
    for script in soup.find_all('script', src=True):
        src = script.get('src')
        if src and not src.startswith('http'):
            if src.startswith('//'):
                script['src'] = f"https:{src}"
            elif src.startswith('/'):
                script['src'] = base_url + src
            else:
                script['src'] = urljoin(base_url, src)
    
    # Resimler
    for img in soup.find_all('img', src=True):
        src = img.get('src')
        if src and not src.startswith('http'):
            if src.startswith('//'):
                img['src'] = f"https:{src}"
            elif src.startswith('/'):
                img['src'] = base_url + src
            else:
                img['src'] = urljoin(base_url, src)


def add_custom_scripts(soup):
    """Custom CSS ve JavaScript ekle"""
    
    # Custom CSS
    style = soup.new_tag('style')
    style.string = """
        /* Proxy view custom styles */
        .proxy-external-link:after {
            content: " 🔗";
            font-size: 0.8em;
            opacity: 0.7;
            color: #1976d2;
        }
        
        .proxy-external-link[href*=".pdf"]:after,
        .proxy-external-link[href*="PDF"]:after {
            content: " 📄";
            font-size: 0.9em;
            opacity: 0.8;
        }
        
        .proxy-external-link:hover {
            background-color: #e3f2fd !important;
            border-radius: 3px;
            padding: 2px 4px;
            transition: all 0.2s ease;
        }
        
        /* Proxy notification */
        .proxy-notification {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            background: #1976d2;
            color: white;
            padding: 8px;
            text-align: center;
            font-size: 14px;
            z-index: 10000;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }
        
        body {
            margin-top: 40px !important;
        }
    """
    
    if soup.head:
        soup.head.append(style)
    
    # Basit JavaScript fallbacks - sadece gerekli olanlar
    jquery_script = soup.new_tag('script')
    jquery_script.string = """
        // Minimal fallbacks for proxy view
        
        // jQuery basic fallback
        if (typeof $ === 'undefined') {
            window.$ = function(selector) {
                if (typeof selector === 'function') {
                    if (document.readyState === 'loading') {
                        document.addEventListener('DOMContentLoaded', selector);
                    } else {
                        selector();
                    }
                }
                return { 
                    ready: function(fn) { 
                        if (document.readyState === 'loading') {
                            document.addEventListener('DOMContentLoaded', fn);
                        } else {
                            fn();
                        }
                        return this;
                    },
                    attr: function() { return ''; },
                    length: 0
                };
            };
        }
        
        // Basic error handling
        window.addEventListener('error', function(e) {
            if (e.message && (e.message.includes('cookie') || e.message.includes('Storage'))) {
                e.preventDefault();
                return false;
            }
        });
    """
    
    script = soup.new_tag('script')
    script.string = """
        // Proxy view custom scripts
        document.addEventListener('DOMContentLoaded', function() {
            console.log('Proxy view loaded - All links will open in new tab');
            
            // Add notification
            var notification = document.createElement('div');
            notification.className = 'proxy-notification';
            notification.innerHTML = '🔗 Proxy View - Tüm linkler yeni sekmede açılır';
            document.body.insertBefore(notification, document.body.firstChild);
            
            // Remove notification after 3 seconds
            setTimeout(function() {
                if (notification && notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                    document.body.style.marginTop = '0';
                }
            }, 3000);
            
            // Ensure all links open in new tab - More aggressive approach
            function handleLinkClick(e) {
                var target = e.target;
                while (target && target.tagName !== 'A') {
                    target = target.parentNode;
                }
                
                if (target && target.tagName === 'A' && target.href) {
                    var href = target.href.toLowerCase();
                    if (!href.startsWith('javascript:') && !href.includes('#') && href !== 'about:blank') {
                        e.preventDefault();
                        e.stopPropagation();
                        window.open(target.href, '_blank', 'noopener,noreferrer');
                        return false;
                    }
                }
            }
            
            // Multiple event listeners for safety
            document.addEventListener('click', handleLinkClick, true);
            document.addEventListener('mousedown', handleLinkClick, true);
        });
    """
    
    if soup.head:
        soup.head.append(jquery_script)
    
    if soup.body:
        soup.body.append(script)


def create_error_response(original_url, article_title, error_type):
    """Hata durumunda HTML response"""
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Sayfa Yüklenemedi</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                max-width: 600px;
                margin: 50px auto;
                padding: 20px;
                background: #f8f9fa;
                text-align: center;
            }}
            .error-container {{
                background: white;
                padding: 30px;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                border-left: 5px solid #e74c3c;
            }}
            .error-icon {{
                font-size: 3rem;
                color: #e74c3c;
                margin-bottom: 20px;
            }}
            h1 {{
                color: #e74c3c;
                margin-bottom: 10px;
            }}
            .btn {{
                display: inline-block;
                background: #3498db;
                color: white;
                padding: 10px 20px;
                text-decoration: none;
                border-radius: 5px;
                margin: 10px 5px;
            }}
            .btn:hover {{
                background: #2980b9;
                color: white;
            }}
        </style>
    </head>
    <body>
        <div class="error-container">
            <div class="error-icon">⚠️</div>
            <h1>Sayfa Yüklenemedi</h1>
            <p><strong>Makale:</strong> {article_title}</p>
            <p><strong>Hata:</strong> {error_type}</p>
            
            <p>Makale sayfası şu anda proxy edilemiyor. Lütfen orijinal linki deneyin.</p>
            
            <div>
                <a href="{original_url}" target="_blank" class="btn">
                    🌐 Orijinal Sayfayı Aç
                </a>
                <a href="javascript:history.back()" class="btn">
                    ⬅️ Geri Dön
                </a>
            </div>
        </div>
    </body>
    </html>
    """
    
    response = HttpResponse(html_content, content_type='text/html')
    response['Cache-Control'] = 'no-cache'
    return response