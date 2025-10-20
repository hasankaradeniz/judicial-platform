# core/pdf_proxy_service.py

import requests
import time
import hashlib
from django.core.cache import cache
from django.http import HttpResponse, Http404
from django.conf import settings
import os
import tempfile


class PDFProxyService:
    """PDF dosyalarını güvenli şekilde proxy eden servis"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/pdf,*/*',
            'Accept-Language': 'en-US,en;q=0.9',
        })
        self.timeout = 30
        self.max_file_size = 50 * 1024 * 1024  # 50MB
    
    def get_pdf_response(self, pdf_url, article_title="document"):
        """PDF URL'ini proxy ederek Django HttpResponse döndür"""
        
        # Cache kontrolü
        cache_key = f'pdf_proxy_{hashlib.md5(pdf_url.encode()).hexdigest()}'
        cached_response = cache.get(cache_key)
        
        if cached_response:
            return self._create_pdf_response(cached_response, article_title)
        
        try:
            print(f"📄 PDF indiriliyor: {pdf_url}")
            
            # PDF'i indir
            response = self.session.get(pdf_url, timeout=self.timeout, stream=True)
            
            if response.status_code == 200:
                # Content-Type kontrolü
                content_type = response.headers.get('content-type', '').lower()
                if 'pdf' not in content_type and 'application/octet-stream' not in content_type:
                    # PDF değilse HTML content oluştur
                    return self._create_html_fallback_response(pdf_url, article_title)
                
                # Dosya boyutu kontrolü
                content_length = response.headers.get('content-length')
                if content_length and int(content_length) > self.max_file_size:
                    return self._create_size_error_response(article_title)
                
                # PDF içeriğini oku
                pdf_content = b''
                downloaded_size = 0
                
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        downloaded_size += len(chunk)
                        if downloaded_size > self.max_file_size:
                            return self._create_size_error_response(article_title)
                        pdf_content += chunk
                
                # PDF content kontrolü
                if pdf_content.startswith(b'%PDF'):
                    # Geçerli PDF - cache'e kaydet (1 saat)
                    cache.set(cache_key, pdf_content, 3600)
                    print(f"✅ PDF başarıyla indirildi: {len(pdf_content)} bytes")
                    return self._create_pdf_response(pdf_content, article_title)
                else:
                    # PDF değil - HTML fallback
                    return self._create_html_fallback_response(pdf_url, article_title)
            
            else:
                print(f"❌ PDF indirme hatası: HTTP {response.status_code}")
                return self._create_error_response(pdf_url, article_title, f"HTTP {response.status_code}")
                
        except requests.exceptions.Timeout:
            print("⏰ PDF indirme timeout")
            return self._create_error_response(pdf_url, article_title, "Timeout")
        except requests.exceptions.RequestException as e:
            print(f"🌐 PDF indirme ağ hatası: {e}")
            return self._create_error_response(pdf_url, article_title, "Network Error")
        except Exception as e:
            print(f"❌ PDF indirme genel hatası: {e}")
            return self._create_error_response(pdf_url, article_title, "General Error")
    
    def _create_pdf_response(self, pdf_content, article_title):
        """PDF content'ini HttpResponse olarak döndür"""
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{self._safe_filename(article_title)}.pdf"'
        response['Cache-Control'] = 'public, max-age=3600'
        response['X-Content-Type-Options'] = 'nosniff'
        return response
    
    def _create_html_fallback_response(self, original_url, article_title):
        """PDF yüklenemediğinde HTML fallback response"""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>{article_title} - PDF Görüntüleyici</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    max-width: 800px;
                    margin: 50px auto;
                    padding: 20px;
                    background: #f5f5f5;
                }}
                .container {{
                    background: white;
                    padding: 30px;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    text-align: center;
                }}
                .icon {{
                    font-size: 4rem;
                    color: #e74c3c;
                    margin-bottom: 20px;
                }}
                h1 {{
                    color: #2c3e50;
                    margin-bottom: 20px;
                }}
                .btn {{
                    display: inline-block;
                    background: #3498db;
                    color: white;
                    padding: 12px 24px;
                    text-decoration: none;
                    border-radius: 5px;
                    margin: 10px;
                    transition: background 0.3s;
                    cursor: pointer;
                    border: none;
                    font-size: 1rem;
                }}
                .btn:hover {{
                    background: #2980b9;
                    color: white;
                }}
                .btn-danger {{
                    background: #e74c3c;
                }}
                .btn-danger:hover {{
                    background: #c0392b;
                }}
                .info {{
                    background: #ecf0f1;
                    padding: 15px;
                    border-radius: 5px;
                    margin: 20px 0;
                    color: #7f8c8d;
                    font-size: 0.9rem;
                }}
            </style>
            <script>
                function openInNewTab() {{
                    window.open('{original_url}', '_blank');
                }}
                
                function openInParentTab() {{
                    if (window.parent && window.parent !== window) {{
                        window.parent.open('{original_url}', '_blank');
                    }} else {{
                        window.open('{original_url}', '_blank');
                    }}
                }}
            </script>
        </head>
        <body>
            <div class="container">
                <div class="icon">📄</div>
                <h1>PDF Görüntüleme</h1>
                <p><strong>Makale:</strong> {article_title}</p>
                
                <div class="info">
                    Bu makale için PDF dosyası iframe içinde görüntülenemiyor. 
                    PDF'i yeni sekmede açmak için aşağıdaki butonu kullanın.
                </div>
                
                <div>
                    <button onclick="openInNewTab()" class="btn">
                        🔗 PDF'i Yeni Sekmede Aç
                    </button>
                    <br>
                    <button onclick="openInParentTab()" class="btn">
                        📤 Ana Pencerede Aç
                    </button>
                    <br>
                    <a href="{original_url}" target="_blank" class="btn">
                        🌐 Orijinal Linke Git
                    </a>
                </div>
                
                <div class="info">
                    <small>
                        💡 <strong>İpucu:</strong> Popup engelleyici etkinse, izin verin veya "Orijinal Linke Git" butonunu kullanın.
                    </small>
                </div>
            </div>
        </body>
        </html>
        """
        
        response = HttpResponse(html_content, content_type='text/html')
        response['Cache-Control'] = 'no-cache'
        return response
    
    def _create_error_response(self, original_url, article_title, error_type):
        """Hata durumunda HTML response"""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>PDF Yükleme Hatası</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    max-width: 600px;
                    margin: 50px auto;
                    padding: 20px;
                    background: #f8f9fa;
                }}
                .error-container {{
                    background: white;
                    padding: 30px;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    text-align: center;
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
                <h1>PDF Yüklenemedi</h1>
                <p><strong>Makale:</strong> {article_title}</p>
                <p><strong>Hata:</strong> {error_type}</p>
                
                <p>PDF dosyası şu anda erişilebilir değil. Lütfen daha sonra tekrar deneyin.</p>
                
                <div>
                    <a href="{original_url}" target="_blank" class="btn">
                        🔗 Orijinal Linki Dene
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
    
    def _create_size_error_response(self, article_title):
        """Dosya boyutu hatası response"""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Dosya Çok Büyük</title>
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; text-align: center; }}
                .container {{ background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .icon {{ font-size: 3rem; color: #f39c12; margin-bottom: 20px; }}
                .btn {{ display: inline-block; background: #3498db; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin: 10px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="icon">📁</div>
                <h1>Dosya Çok Büyük</h1>
                <p><strong>Makale:</strong> {article_title}</p>
                <p>PDF dosyası çok büyük (50MB+). Güvenlik nedeniyle görüntülenemiyor.</p>
                <a href="javascript:history.back()" class="btn">⬅️ Geri Dön</a>
            </div>
        </body>
        </html>
        """
        
        response = HttpResponse(html_content, content_type='text/html')
        return response
    
    def _safe_filename(self, filename):
        """Güvenli dosya adı oluştur"""
        import re
        # Türkçe karakterleri değiştir
        replacements = {
            'ç': 'c', 'ğ': 'g', 'ı': 'i', 'ö': 'o', 'ş': 's', 'ü': 'u',
            'Ç': 'C', 'Ğ': 'G', 'İ': 'I', 'Ö': 'O', 'Ş': 'S', 'Ü': 'U'
        }
        
        for turkish, english in replacements.items():
            filename = filename.replace(turkish, english)
        
        # Sadece güvenli karakterleri bırak
        filename = re.sub(r'[^a-zA-Z0-9_\-\s]', '', filename)
        filename = re.sub(r'\s+', '_', filename.strip())
        
        # Uzunluk sınırla
        if len(filename) > 50:
            filename = filename[:50]
        
        return filename or "academic_article"


def proxy_pdf_view(request, source, article_id):
    """PDF proxy view fonksiyonu"""
    
    # Session'dan makale bilgilerini al
    session_key = f'article_{article_id}'
    article = request.session.get(session_key)
    
    if not article:
        raise Http404("Makale bulunamadı")
    
    pdf_url = article.get('pdf_link') or article.get('detail_link')
    article_title = article.get('title', 'Academic Article')
    
    if not pdf_url:
        raise Http404("PDF linki bulunamadı")
    
    # PDF proxy servisini kullan
    proxy_service = PDFProxyService()
    return proxy_service.get_pdf_response(pdf_url, article_title)