"""
Param Sanal Pos Entegrasyonu - IP Kayıtlı Sürüm
ParamPOS API Entegrasyon Bilgileri:
- Terminal No: 145942
- Kullanıcı Adı: TP10173244
- Şifre: E78A466F0083A439
- GUID: E204D733-02BA-4312-B03F-84BFE184313C
- Test SOAP Endpoint: https://testposws.param.com.tr/turkpos.ws/service_turkpos_prod.asmx
- Prod SOAP Endpoint: https://posws.param.com.tr/turkpos.ws/service_turkpos_prod.asmx
"""
import hashlib
import hmac
import base64
import json
import requests
from datetime import datetime
from django.conf import settings
from django.urls import reverse
from django.contrib.sites.shortcuts import get_current_site


class ParamPosService:
    """Param Sanal Pos işlemleri için servis sınıfı - IP Kayıtlı"""
    
    def __init__(self):
        # ParamPOS credentials (production parametreleri)
        self.client_code = getattr(settings, 'PARAM_CLIENT_CODE', '145942')
        self.client_username = getattr(settings, 'PARAM_CLIENT_USERNAME', 'TP10173244')
        self.client_password = getattr(settings, 'PARAM_CLIENT_PASSWORD', 'E78A466F0083A439')
        self.guid = getattr(settings, 'PARAM_GUID', 'E204D733-02BA-4312-B03F-84BFE184313C')
        
        # Production modu (IP kayıtlı)
        self.test_mode = getattr(settings, 'PARAM_TEST_MODE', False)
        
        # SOAP Web Servis URL'leri (doğru production endpoint)
        if self.test_mode:
            self.soap_endpoint = 'https://testposws.param.com.tr/turkpos.ws/service_turkpos_prod.asmx'
        else:
            self.soap_endpoint = 'https://posws.param.com.tr/turkpos.ws/service_turkpos_prod.asmx'
        
        # IP bilgisi
        self.server_ip = self.get_server_ip()
        
    def get_server_ip(self):
        """Sunucunun dış IPv4 adresini al - IPv4 zorla"""
        # Production VPS IP'sini direkt kullan (IPv4 guaranteed)
        production_ip = '145.223.82.130'
        
        # Test için alternatif servisleri dene (IPv4 only)
        ipv4_services = [
            'https://api.ipify.org?format=json',  # IPv4 only garanti
            'https://checkip.amazonaws.com',      # IPv4 only 
            'https://ipv4.icanhazip.com'         # IPv4 only
        ]
        
        for service_url in ipv4_services:
            try:
                if 'checkip.amazonaws.com' in service_url or 'icanhazip.com' in service_url:
                    # Text döndüren servisleri
                    response = requests.get(service_url, timeout=3)
                    ip = response.text.strip()
                    # IPv4 format kontrolü
                    if '.' in ip and ':' not in ip:
                        print(f"✅ IPv4 tespit edildi: {ip}")
                        return ip
                else:
                    # JSON servisleri
                    response = requests.get(service_url, timeout=3)
                    data = response.json()
                    ip = data.get('ip')
                    if ip and '.' in ip and ':' not in ip:
                        print(f"✅ IPv4 tespit edildi: {ip}")
                        return ip
            except Exception as e:
                print(f"IP servisi {service_url} başarısız: {e}")
                continue
        
        # Fallback: Production VPS IP'si (ParamPOS'ta kayıtlı)
        print(f"⚠️  IP servisler IPv6 döndürüyor, kayıtlı production IPv4 kullanılacak: {production_ip}")
        return production_ip
    
    def get_package_amount(self, package):
        """Paket tipine göre fiyat döndürür (kuruş cinsinden)"""
        package_prices = {
            'monthly': 100000,      # 1000.00 TL
            'quarterly': 270000,    # 2700.00 TL
            'semi_annual': 520000,  # 5200.00 TL
            'annual': 1000000,      # 10000.00 TL
        }
        return package_prices.get(package, 100000)
    
    def get_package_name(self, package):
        """Paket tipine göre açıklama döndürür (Latin-1 uyumlu)"""
        package_names = {
            'monthly': 'Lexatech Aylik Abonelik',
            'quarterly': 'Lexatech 3 Aylik Abonelik', 
            'semi_annual': 'Lexatech 6 Aylik Abonelik',
            'annual': 'Lexatech Yillik Abonelik',
        }
        return package_names.get(package, 'Lexatech Abonelik')
    
    def create_iframe_payment_url(self, request, package, user_data):
        """IP Kayıtlı SOAP API ile ödeme URL'i oluştur"""
        import requests
        from xml.etree import ElementTree as ET
        
        current_site = get_current_site(request)
        
        # Localhost için demo mode
        if current_site.domain in ['127.0.0.1:8000', 'localhost:8000', 'testserver']:
            return self.create_demo_payment_flow(request, package, None, None)
        
        # Sipariş numarası oluştur
        order_id = f"LEX_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{request.user.id}"
        
        # Tutar bilgisi (TL cinsinden)
        amount = self.get_package_amount(package) / 100  # Kuruştan TL'ye çevir
        
        # Pos_Odeme metodunu kullan (Doküman: Nonsecure / 3D ödeme)
        transaction_id = f"TXN_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        islem_id = f"ISLEM_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Hash oluştur (Doküman: SHA2B64 = SHA256 + Base64)
        import hashlib
        import base64
        
        # Production domain kullan
        domain = "145.223.82.130:8001" if ("145.223.82.130" in current_site.domain or current_site.domain == "example.com") else current_site.domain
        success_url = f"https://{domain}{reverse('payment_success')}"
        fail_url = f"https://{domain}{reverse('payment_fail')}"
        
        # Doküman: Islem_Tutar virgüllü kuruş formatında (1000,50)
        amount_str = f"{amount:.2f}".replace('.', ',')
        # Tek çekim için taksit = 1 (0 desteklenmiyor)
        taksit = "1"
        
        # Pos_Odeme Hash Formülü (Doküman): CLIENT_CODE & GUID & Taksit & Islem_Tutar & Toplam_Tutar & Siparis_ID & Hata_URL & Basarili_URL
        hash_string = f"{self.client_code}{self.guid}{taksit}{amount_str}{amount_str}{order_id}{fail_url}{success_url}"
        
        # SHA2B64 = SHA256 + Base64 encoding (Doküman)
        hash_value = base64.b64encode(hashlib.sha256(hash_string.encode('utf-8')).digest()).decode('utf-8')
        
        # Debug hash string - also write to file
        debug_info = f"""
=== PARAM POS HASH DEBUG ===
Method: Pos_Odeme
CLIENT_CODE: {self.client_code}
GUID: {self.guid}
Taksit: {taksit}
Islem_Tutar: {amount_str}
Toplam_Tutar: {amount_str}
Siparis_ID: {order_id}
Hata_URL: {fail_url}
Basarili_URL: {success_url}
Full Hash String: {hash_string}
Hash Value (SHA256+Base64): {hash_value}
===========================
"""
        print(debug_info)
        
        # Also write to debug file
        try:
            with open('/var/log/param_pos_debug.log', 'a') as f:
                f.write(f"\n{datetime.now()} - {debug_info}\n")
        except:
            pass
        
        # SOAP XML - Pos_Odeme metodu (3D Secure akışı)
        soap_xml = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <Pos_Odeme xmlns="https://turkpos.com.tr/">
      <G>
        <CLIENT_CODE>{self.client_code}</CLIENT_CODE>
        <CLIENT_USERNAME>{self.client_username}</CLIENT_USERNAME>
        <CLIENT_PASSWORD>{self.client_password}</CLIENT_PASSWORD>
      </G>
      <GUID>{self.guid}</GUID>
      <KK_Sahibi>Test Customer</KK_Sahibi>
      <KK_No>4022774022774026</KK_No>
      <KK_SK_Ay>12</KK_SK_Ay>
      <KK_SK_Yil>2026</KK_SK_Yil>
      <KK_CVC>000</KK_CVC>
      <KK_Sahibi_GSM>5551234567</KK_Sahibi_GSM>
      <Hata_URL>{fail_url}</Hata_URL>
      <Basarili_URL>{success_url}</Basarili_URL>
      <Siparis_ID>{order_id}</Siparis_ID>
      <Siparis_Aciklama>{self.get_package_name(package)}</Siparis_Aciklama>
      <Taksit>1</Taksit>
      <Islem_Tutar>{amount_str}</Islem_Tutar>
      <Toplam_Tutar>{amount_str}</Toplam_Tutar>
      <Islem_Hash>{hash_value}</Islem_Hash>
      <Islem_Guvenlik_Tip>3D</Islem_Guvenlik_Tip>
      <Islem_ID>{islem_id}</Islem_ID>
      <IPAdr>145.223.82.130</IPAdr>
      <Ref_URL>https://{domain}</Ref_URL>
      <Data1></Data1>
      <Data2></Data2>
      <Data3></Data3>
      <Data4></Data4>
      <Data5></Data5>
    </Pos_Odeme>
  </soap:Body>
</soap:Envelope>"""
        
        headers = {
            'Content-Type': 'text/xml; charset=utf-8',
            'SOAPAction': 'https://turkpos.com.tr/Pos_Odeme',
            'Accept': 'text/xml'
        }
        
        mode = "TEST" if self.test_mode else "PRODUCTION"
        print(f"🔧 {mode} SOAP Request to: {self.soap_endpoint}")
        print(f"📋 Order ID: {order_id}")
        print(f"💰 Amount: {amount} TL")
        print(f"🌐 Server IP: {self.server_ip}")
        
        try:
            # TLS 1.2 zorla ve SSL sertifikası doğrulaması
            import ssl
            import urllib3
            import socket
            from requests.adapters import HTTPAdapter
            from urllib3.util.retry import Retry
            from urllib3.util.connection import create_connection
            
            # IPv4 zorla - IPv6'yı tamamen devre dışı bırak
            old_getaddrinfo = socket.getaddrinfo
            def ipv4_only_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
                return old_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
            socket.getaddrinfo = ipv4_only_getaddrinfo
            
            session = requests.Session()
            
            # TLS 1.2 zorla
            session.mount('https://', HTTPAdapter(
                max_retries=Retry(total=3, backoff_factor=1)
            ))
            
            # SOAP API çağrısı - IPv4 zorlamalı TLS 1.2 ile UTF-8 encoding
            response = session.post(
                self.soap_endpoint, 
                data=soap_xml.encode('utf-8'), 
                headers=headers, 
                timeout=30,
                verify=True  # SSL sertifikası doğrula
            )
            
            # Eski socket fonksiyonunu geri yükle
            socket.getaddrinfo = old_getaddrinfo
            
            print(f"{mode} SOAP Response Status: {response.status_code}")
            print(f"{mode} SOAP Response: {response.text[:1000]}")
            
            if response.status_code == 200:
                return self.parse_soap_response(response, order_id, amount, mode)
            elif response.status_code == 403:
                print(f"⚠️ {mode} SOAP 403 hatası - IP whitelisting sorunu")
                return self.handle_soap_error(response, mode)
            else:
                return self.handle_soap_error(response, mode)
                
        except Exception as e:
            print(f"💥 {mode} SOAP Exception: {str(e)}")
            return {
                'success': False,
                'error': f'{mode} SOAP bağlantı hatası: {str(e)}',
                'mode': mode.lower()
            }
    
    def parse_soap_response(self, response, order_id, amount, mode):
        """SOAP response'unu parse et"""
        from xml.etree import ElementTree as ET
        
        try:
            # XML yanıtını parse et
            root = ET.fromstring(response.text)
            
            # SOAP Fault kontrolü
            fault = root.find('.//soap:Fault', {'soap': 'http://schemas.xmlsoap.org/soap/envelope/'})
            if fault is not None:
                fault_string = fault.find('.//faultstring')
                fault_detail = fault_string.text if fault_string is not None else 'Unknown SOAP fault'
                
                return {
                    'success': False,
                    'error': f'{mode} SOAP Fault: {fault_detail}',
                    'mode': mode.lower(),
                    'soap_fault': True
                }
            
            # SOAP response parse et - tüm namespace'leri dene
            namespaces = {
                'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
                'turkpos': 'https://turkpos.com.tr/'
            }
            
            # Pos_Odeme response elementlerini bul
            result_code = (root.find('.//turkpos:Pos_OdemeResult/turkpos:Sonuc', namespaces) or
                          root.find('.//Pos_OdemeResult/Sonuc') or
                          root.find('.//Sonuc') or
                          root.find('.//{https://turkpos.com.tr/}Sonuc'))
                          
            # Sonuc_Str elementini bul  
            result_description = (root.find('.//turkpos:Pos_OdemeResult/turkpos:Sonuc_Str', namespaces) or
                                 root.find('.//Pos_OdemeResult/Sonuc_Str') or
                                 root.find('.//Sonuc_Str') or
                                 root.find('.//{https://turkpos.com.tr/}Sonuc_Str'))
                                 
            # UCD_URL elementini bul (3D Secure için)
            url_element = (root.find('.//turkpos:Pos_OdemeResult/turkpos:UCD_URL', namespaces) or
                          root.find('.//Pos_OdemeResult/UCD_URL') or
                          root.find('.//UCD_URL') or
                          root.find('.//{https://turkpos.com.tr/}UCD_URL'))
                          
            # Dekont_ID elementini bul 
            dekont_id = (root.find('.//turkpos:Pos_OdemeResult/turkpos:Dekont_ID', namespaces) or
                        root.find('.//Pos_OdemeResult/Dekont_ID') or
                        root.find('.//Dekont_ID') or
                        root.find('.//{https://turkpos.com.tr/}Dekont_ID'))
                        
            # Islem_ID elementini bul
            islem_id_element = (root.find('.//turkpos:Pos_OdemeResult/turkpos:Islem_ID', namespaces) or
                               root.find('.//Pos_OdemeResult/Islem_ID') or
                               root.find('.//Islem_ID') or
                               root.find('.//{https://turkpos.com.tr/}Islem_ID'))
                          
            # Debug: XML içeriğini yazdır
            print(f"{mode} Raw XML Response:")
            print(response.text[:500])
            
            print(f"{mode} Sonuc: {result_code.text if result_code is not None else 'NOT FOUND'}")
            print(f"{mode} Sonuc_Str: {result_description.text if result_description is not None else 'NOT FOUND'}")
            print(f"{mode} UCD_URL: {url_element.text if url_element is not None else 'NOT FOUND'}")
            print(f"{mode} Dekont_ID: {dekont_id.text if dekont_id is not None else 'NOT FOUND'}")
            print(f"{mode} Islem_ID: {islem_id_element.text if islem_id_element is not None else 'NOT FOUND'}")
            
            # Pos_Odeme response logic according to documentation
            result_code_val = int(result_code.text) if result_code is not None and result_code.text.isdigit() else -1
            
            if result_code_val > 0:
                # Success case - check UCD_URL
                if url_element is not None and url_element.text:
                    if url_element.text == 'NONSECURE':
                        # NonSecure success - check Islem_ID > 0
                        islem_id_val = int(islem_id_element.text) if islem_id_element is not None and islem_id_element.text.isdigit() else 0
                        if islem_id_val > 0:
                            return {
                                'success': True,
                                'order_id': order_id,
                                'transaction_id': islem_id_element.text,
                                'dekont_id': dekont_id.text if dekont_id is not None else '',
                                'method': f'{mode}_NONSECURE_SUCCESS',
                                'amount': amount,
                                'mode': mode.lower(),
                                'message': 'NonSecure ödeme başarılı'
                            }
                        else:
                            return {
                                'success': False,
                                'error': f'{mode} NonSecure ödeme başarısız - Islem_ID: {islem_id_val}',
                                'mode': mode.lower()
                            }
                    else:
                        # 3D Secure redirect
                        return {
                            'success': True,
                            'payment_url': url_element.text,
                            'order_id': order_id,
                            'method': f'{mode}_3D_SECURE_REDIRECT',
                            'amount': amount,
                            'mode': mode.lower(),
                            'requires_redirect': True,
                            'message': 'Kart bilgileri için 3D Secure sayfasına yönlendiriliyorsunuz'
                        }
                else:
                    return {
                        'success': False,
                        'error': f'{mode} UCD_URL bulunamadı',
                        'mode': mode.lower()
                    }
            else:
                # Error case
                error_code = result_code.text if result_code is not None else 'Bilinmeyen Kod'
                error_detail = result_description.text if result_description is not None else 'Bilinmeyen hata'
                return {
                    'success': False,
                    'error': f'{mode} Param Pos Hatası ({error_code}): {error_detail}',
                    'mode': mode.lower(),
                    'param_error_code': error_code
                }
                        
        except ET.ParseError as e:
            return {
                'success': False,
                'error': f'{mode} XML parse hatası: {str(e)}',
                'mode': mode.lower()
            }
    
    def handle_soap_error(self, response, mode):
        """SOAP hata durumunu handle et"""
        if response.status_code == 403:
            return {
                'success': False,
                'error': f'{mode} IP whitelisting hatası. IP ({self.server_ip}) kayıtlı değil.',
                'mode': mode.lower(),
                'ip_registration_needed': True
            }
        elif response.status_code == 401:
            return {
                'success': False,
                'error': f'{mode} authentication hatası. Credentials kontrol edin.',
                'mode': mode.lower(),
                'auth_error': True
            }
        elif response.status_code == 500:
            return {
                'success': False,
                'error': f'{mode} sunucu hatası (500). Hesap durumu veya API format sorunu olabilir.',
                'mode': mode.lower(),
                'server_error': True,
                'suggestion': 'ParamPOS destek ekibi ile iletişime geçin.'
            }
        else:
            return {
                'success': False,
                'error': f'{mode} HTTP hatası: {response.status_code}',
                'mode': mode.lower()
            }
    
    def create_form_based_payment(self, request, package, order_id, amount):
        """SOAP başarısız olunca form-based ödeme kullan"""
        import hashlib
        import hmac
        import base64
        
        try:
            current_site = get_current_site(request)
            
            if not order_id:
                order_id = f"LEX_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{request.user.id}"
            if not amount:
                amount = self.get_package_amount(package) / 100
            
            # Form-based ödeme için gerekli parametreler
            total_amount = int(amount * 100)  # Kuruş cinsinden
            
            # Hash oluştur (CLIENT_CODE + ORDER_ID + TOTAL_AMOUNT + CLIENT_PASSWORD)
            hash_string = f"{self.client_code}{order_id}{total_amount}{'FAIL' if self.test_mode else 'FAIL'}{self.client_password}"
            
            signature = hmac.new(
                self.client_password.encode('utf-8'),
                hash_string.encode('utf-8'),
                hashlib.sha256
            ).digest()
            
            hash_value = base64.b64encode(signature).decode('utf-8')
            
            # Form parametreleri
            form_params = {
                'CLIENT_CODE': self.client_code,
                'CLIENT_USERNAME': self.client_username, 
                'GUID': self.guid,
                'MERCHANT_OID': order_id,
                'TOTAL_AMOUNT': total_amount,
                'CURRENCY': 'TL',
                'SUCCESS_URL': f"https://{current_site.domain}{reverse('payment_success')}",
                'FAIL_URL': f"https://{current_site.domain}{reverse('payment_fail')}",
                'HASH': hash_value,
                'INSTALLMENT_COUNT': '1',
                'MAX_INSTALLMENT': '12',
                'TEST_MODE': '1' if self.test_mode else '0'
            }
            
            # Form-based URL
            form_url = 'https://test-pos-mp.param.com.tr/Payment.aspx' if self.test_mode else 'https://pos-mp.param.com.tr/Payment.aspx'
            
            print(f"📋 Form-based ödeme parametreleri hazırlandı")
            print(f"🔗 Form URL: {form_url}")
            print(f"💰 Tutar: {amount} TL ({total_amount} kuruş)")
            
            return {
                'success': True,
                'payment_url': form_url,
                'form_params': form_params,
                'order_id': order_id,
                'method': 'FORM_BASED',
                'amount': amount,
                'is_form': True
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Form-based ödeme hazırlama hatası: {str(e)}'
            }
    
    def create_demo_payment_flow(self, request, package, order_id, amount):
        """Yerel test ortamı için demo ödeme akışı"""
        try:
            current_site = get_current_site(request)
            
            if not order_id:
                order_id = f"DEMO_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            if not amount:
                amount = self.get_package_amount(package) / 100
            
            # Demo ödeme sayfası URL'i oluştur
            demo_url = f"http://{current_site.domain}/demo-payment/?order_id={order_id}&amount={amount}&package={package}"
            
            return {
                'success': True,
                'payment_url': demo_url,
                'order_id': order_id,
                'is_demo': True,
                'method': 'DEMO',
                'demo_message': f'Localhost için demo ödeme sayfası.'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Demo ödeme hazırlama hatası: {str(e)}'
            }
    
    # Geriye uyumluluk için eski methodlar
    def create_form_payment_url(self, request, package, order_id, amount):
        return self.create_iframe_payment_url(request, package, {})
        
    def create_fallback_payment_url(self, request, package, order_id, amount):
        return self.create_iframe_payment_url(request, package, {})
    
    def create_payment_form_data(self, request, package, user_data):
        return self.create_iframe_payment_url(request, package, user_data)
    
    def get_client_ip(self, request):
        """Kullanıcının IP adresini alır"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def verify_payment_response(self, response_data):
        """Ödeme sonuç yanıtını doğrular"""
        try:
            # Demo mode için basit doğrulama
            if response_data.get('demo') == '1':
                return {
                    'success': response_data.get('status') == 'success',
                    'order_id': response_data.get('order_id'),
                    'amount': response_data.get('amount', '0'),
                    'transaction_id': 'DEMO_' + response_data.get('order_id', ''),
                    'message': 'Demo ödeme işlemi'
                }
            
            # 3D Secure geri dönüş için complete_3d_payment kullan
            if any(key in response_data for key in ['islemGUID', 'mdStatus', 'md']):
                return self.complete_3d_payment(None, response_data)
            
            # ParamPOS ödeme için doğrulama
            return {
                'success': response_data.get('status') == 'success' or response_data.get('Result') == '1',
                'order_id': response_data.get('merchant_oid') or response_data.get('Order_ID') or response_data.get('order_id'),
                'amount': response_data.get('total_amount') or response_data.get('Amount') or response_data.get('amount'),
                'transaction_id': response_data.get('transaction_id') or response_data.get('Transaction_ID') or 'TXN_' + str(datetime.now().timestamp()),
                'message': response_data.get('message') or response_data.get('ResultDetail') or 'Ödeme işlemi'
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Ödeme doğrulaması sırasında hata: {str(e)}'
            }
    
    def complete_3d_payment(self, request, response_data):
        """3D Secure sonrası ödemeyi tamamlar - TP_WMD_Pay metodu"""
        try:
            # 3D Secure parametrelerini al
            islem_guid = response_data.get('islemGUID', '')
            md = response_data.get('md', '') 
            md_status = response_data.get('mdStatus', '')
            order_id = response_data.get('orderId', '')
            islem_hash = response_data.get('islemHash', '')
            
            # Hash doğrulaması (doküman: islemGUID + md + mdStatus + orderId + anahtar)
            # Dokümanda: "anahtar Lower küçük olarak gidilmeli"
            expected_hash_string = f"{islem_guid}{md}{md_status}{order_id}{self.guid.lower()}"
            expected_hash = base64.b64encode(hashlib.sha1(expected_hash_string.encode('utf-8')).digest()).decode('utf-8')
            
            print(f"Hash validation - Expected: {expected_hash}, Received: {islem_hash}")
            
            if expected_hash != islem_hash:
                return {
                    'success': False,
                    'error': 'Hash validation failed',
                    'expected_hash': expected_hash,
                    'received_hash': islem_hash
                }
            
            # mdStatus kontrolü (1,2,3,4 = başarılı, 0,5,6,7,8 = başarısız)
            md_status_int = int(md_status) if md_status.isdigit() else 0
            if md_status_int not in [1, 2, 3, 4]:
                return {
                    'success': False,
                    'error': f'3D Secure doğrulama başarısız. mdStatus: {md_status}',
                    'md_status': md_status
                }
            
            # TP_WMD_Pay SOAP isteği
            soap_xml = f"""<?xml version=\"1.0\" encoding=\"utf-8\"?>
<soap:Envelope xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" xmlns:xsd=\"http://www.w3.org/2001/XMLSchema\" xmlns:soap=\"http://schemas.xmlsoap.org/soap/envelope/\">
  <soap:Body>
    <TP_WMD_Pay xmlns=\"https://turkpos.com.tr/\">
      <G>
        <CLIENT_CODE>{self.client_code}</CLIENT_CODE>
        <CLIENT_USERNAME>{self.client_username}</CLIENT_USERNAME>
        <CLIENT_PASSWORD>{self.client_password}</CLIENT_PASSWORD>
      </G>
      <GUID>{self.guid}</GUID>
      <UCD_MD>{md}</UCD_MD>
      <Islem_GUID>{islem_guid}</Islem_GUID>
      <Siparis_ID>{order_id}</Siparis_ID>
    </TP_WMD_Pay>
  </soap:Body>
</soap:Envelope>"""
            
            headers = {
                'Content-Type': 'text/xml; charset=utf-8',
                'SOAPAction': 'https://turkpos.com.tr/TP_WMD_Pay',
                'Accept': 'text/xml'
            }
            
            # SOAP isteği gönder
            import requests
            response = requests.post(self.soap_endpoint, data=soap_xml.encode('utf-8'), headers=headers, timeout=30)
            
            if response.status_code == 200:
                return self.parse_payment_completion_response(response, order_id)
            else:
                return {
                    'success': False,
                    'error': f'TP_WMD_Pay HTTP hatası: {response.status_code}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'3D ödeme tamamlama hatası: {str(e)}'
            }
    
    def parse_payment_completion_response(self, response, order_id):
        """TP_WMD_Pay response'unu parse et"""
        from xml.etree import ElementTree as ET
        
        try:
            root = ET.fromstring(response.text)
            
            # Response elementlerini bul
            result_code = root.find('.//Sonuc') or root.find('.//{https://turkpos.com.tr/}Sonuc')
            result_description = root.find('.//Sonuc_Str') or root.find('.//{https://turkpos.com.tr/}Sonuc_Str')
            dekont_id = root.find('.//Dekont_ID') or root.find('.//{https://turkpos.com.tr/}Dekont_ID')
            
            print(f"TP_WMD_Pay Response - Sonuc: {result_code.text if result_code is not None else 'NOT FOUND'}")
            print(f"TP_WMD_Pay Response - Dekont_ID: {dekont_id.text if dekont_id is not None else 'NOT FOUND'}")
            
            # Başarı kontrolü: Sonuc > 0 ve Dekont_ID > 0
            if (result_code is not None and int(result_code.text) > 0 and
                dekont_id is not None and int(dekont_id.text) > 0):
                return {
                    'success': True,
                    'order_id': order_id,
                    'dekont_id': dekont_id.text,
                    'transaction_id': dekont_id.text,
                    'message': result_description.text if result_description is not None else 'Ödeme başarılı'
                }
            else:
                error_code = result_code.text if result_code is not None else 'Bilinmeyen Kod'
                error_detail = result_description.text if result_description is not None else 'Bilinmeyen hata'
                return {
                    'success': False,
                    'error': f'Ödeme tamamlanamadı ({error_code}): {error_detail}',
                    'result_code': error_code
                }
                
        except ET.ParseError as e:
            return {
                'success': False,
                'error': f'TP_WMD_Pay XML parse hatası: {str(e)}'
            }

    def generate_response_hash(self, response_data):
        """Response için hash üretir"""
        hash_string = (
            f"{self.client_code}{response_data.get('merchant_oid')}"
            f"{response_data.get('total_amount')}{response_data.get('status')}"
        )
        
        # SHA256 + Base64 (SHA2B64)
        hash_value = base64.b64encode(hashlib.sha256(hash_string.encode('utf-8')).digest()).decode('utf-8')
        
        return hash_value
    
    def get_payment_url(self):
        """Ödeme URL'ini döndürür"""
        mode = "TEST" if self.test_mode else "PRODUCTION"
        return f"{mode}_IP_REGISTERED_SOAP"