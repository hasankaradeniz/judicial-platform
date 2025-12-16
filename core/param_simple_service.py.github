"""
Param Sanal POS Entegrasyonu - Basitleştirilmiş Versiyon
Flask örneğinden Django'ya uyarlanmış hali
"""

import hashlib
import base64
import requests
import re
from datetime import datetime
from django.conf import settings
import html
from django.urls import reverse
from django.contrib.sites.shortcuts import get_current_site
import logging

logger = logging.getLogger(__name__)


class ParamSimpleService:
    """Param Sanal POS servisi - Basitleştirilmiş versiyon"""
    
    def __init__(self):
        # Param credentials
        self.client_code = "10738" if getattr(settings, "PARAM_TEST_MODE", False) else getattr(settings, "PARAM_CLIENT_CODE", "145942")
        self.username = "test" if getattr(settings, "PARAM_TEST_MODE", False) else getattr(settings, "PARAM_CLIENT_USERNAME", "TP10173244")
        self.password = "test" if getattr(settings, "PARAM_TEST_MODE", False) else getattr(settings, "PARAM_CLIENT_PASSWORD", "E78A466F0083A439")
        self.guid = "0C13D406-873B-403B-9C09-A5766840D98C" if getattr(settings, "PARAM_TEST_MODE", False) else getattr(settings, "PARAM_GUID", "E204D733-02BA-4312-B03F-84BFE184313C")
        
        # Test/Production mode - Set to False for production
        self.test_mode = getattr(settings, 'PARAM_TEST_MODE', False)
        
        # Service URLs - SOAP endpoints for Param POS
        if self.test_mode:
            self.soap_url = 'https://testposws.param.com.tr/turkpos.ws/service_turkpos_prod.asmx'
        else:
            self.soap_url = 'https://posws.param.com.tr/turkpos.ws/service_turkpos_prod.asmx'
    
    def get_package_amount(self, package_type):
        """Paket fiyatları (kuruş cinsinden)"""
        prices = {
            'monthly': 100000,      # 1000.00 TL
            'quarterly': 270000,    # 2700.00 TL  
            'semi_annual': 520000,  # 5200.00 TL
            'annual': 1000000,      # 10000.00 TL
        }
        return prices.get(package_type, 100000)
    
    def get_package_description(self, package_type):
        """Paket açıklamaları"""
        descriptions = {
            'monthly': 'Lexatech Aylik Abonelik',
            'quarterly': 'Lexatech 3 Aylik Abonelik',
            'semi_annual': 'Lexatech 6 Aylik Abonelik', 
            'annual': 'Lexatech Yillik Abonelik',
        }
        return descriptions.get(package_type, 'Lexatech Abonelik')
    
    def sha1b64_hash(self, params):
        """SHA1 ile hash alıp Base64'e çevirir"""
        h = hashlib.sha1(params.encode("utf-8")).digest()
        return base64.b64encode(h).decode("utf-8")
    
    def start_payment(self, request, package_type, user_data):
        """Ödeme işlemini başlat - TP_WMD_UCD ile 3D Secure"""
        try:
            current_site = get_current_site(request)
            
            # Demo mode check
            if current_site.domain in ['127.0.0.1:8000', 'localhost:8000', 'testserver']:
                return self.create_demo_payment(request, package_type)
            
            # Order details
            order_id = f"LEX_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{request.user.id}"
            amount_kurus = self.get_package_amount(package_type)
            amount_tl = amount_kurus / 100
            amount_str = f"{amount_tl:.2f}".replace('.', ',')
            
            # URLs
            domain = current_site.domain
            if domain == 'example.com' or '145.223.82.130' in domain:
                domain = 'lexatech.ai'
            
            success_url = f"https://{domain}{reverse('payment_success')}"
            fail_url = f"https://{domain}{reverse('payment_fail')}"
            
            # Hash calculation for TP_WMD_UCD
            taksit = "1"
            hash_string = f"{self.client_code}{self.guid.lower()}{taksit}{amount_str}{amount_str}{order_id}"
            logger.info(f"Hash string: {hash_string}")
            logger.info(f"Calculated hash: {self.sha1b64_hash(hash_string)}")
            hash_value = self.sha1b64_hash(hash_string)
            
            # Transaction ID
            transaction_id = f"TXN_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # SOAP XML for TP_WMD_UCD
            soap_body = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
               xmlns:xsd="http://www.w3.org/2001/XMLSchema" 
               xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <TP_WMD_UCD xmlns="https://turkpos.com.tr/">
      <G>
        <CLIENT_CODE>{self.client_code}</CLIENT_CODE>
        <CLIENT_USERNAME>{self.username}</CLIENT_USERNAME>
        <CLIENT_PASSWORD>{self.password}</CLIENT_PASSWORD>
      </G>
      <GUID>{self.guid.lower()}</GUID>
      <KK_Sahibi>{user_data.get('card_owner', 'Test Customer')}</KK_Sahibi>
      <KK_No>{user_data.get('card_number', '4022774022774026')}</KK_No>
      <KK_SK_Ay>{user_data.get('expire_month', '12')}</KK_SK_Ay>
      <KK_SK_Yil>{user_data.get('expire_year', '2026')}</KK_SK_Yil>
      <KK_CVC>{user_data.get('cvc', '000')}</KK_CVC>
      <KK_Sahibi_GSM>{user_data.get('gsm', '5551234567')}</KK_Sahibi_GSM>
      <Hata_URL>{fail_url}</Hata_URL>
      <Basarili_URL>{success_url}</Basarili_URL>
      <Siparis_ID>{order_id}</Siparis_ID>
      <Siparis_Aciklama>{self.get_package_description(package_type)}</Siparis_Aciklama>
      <Taksit>{taksit}</Taksit>
      <Islem_Tutar>{amount_str}</Islem_Tutar>
      <Toplam_Tutar>{amount_str}</Toplam_Tutar>
      <Islem_Hash>{hash_value}</Islem_Hash>
      <Islem_Guvenlik_Tip>3D</Islem_Guvenlik_Tip>
      <Islem_ID>{transaction_id}</Islem_ID>
      <IPAdr>{self.get_client_ip(request)}</IPAdr>
      <Ref_URL>https://{domain}</Ref_URL>
      <Data1></Data1>
      <Data2></Data2>
      <Data3></Data3>
      <Data4></Data4>
      <Data5></Data5>
    </TP_WMD_UCD>
  </soap:Body>
</soap:Envelope>"""
            
            # SOAP headers
            headers = {
                'Content-Type': 'text/xml; charset=utf-8',
                'SOAPAction': 'https://turkpos.com.tr/TP_WMD_UCD',
                'Accept': 'text/xml'
            }
            
            logger.info(f"Sending TP_WMD_UCD request - Order: {order_id}, Amount: {amount_tl} TL")
            logger.info(f"SOAP Request: {soap_body[:500]}...")
            
            response = requests.post(
                self.soap_url,
                data=soap_body.encode('utf-8'),
                headers=headers,
                timeout=30,
                verify=True
            )
            
            if response.status_code == 200:
                return self.parse_tp_wmd_ucd_response(response, order_id, amount_tl)
            elif response.status_code == 403:
                logger.error("IP not whitelisted - Access Denied")
                return {"success": False, "error": "SOAP isteği başarısız - fallback devre dışı", "order_id": order_id}
            else:
                logger.error(f"SOAP request failed: {response.status_code}")
                return {
                    'success': False,
                    'error': f'HTTP {response.status_code}: {response.text[:200]}',
                    'order_id': order_id
                }
                
        except Exception as e:
            logger.error(f"Payment start error: {str(e)}")
            return {"success": False, "error": "SOAP isteği başarısız - fallback devre dışı", "order_id": order_id}
    
    def parse_tp_wmd_ucd_response(self, response, order_id, amount):
        """TP_WMD_UCD response parse et"""
        try:
            logger.info(f"TP_WMD_UCD Response: {response.text}")
            
            # Parse XML response
            match = re.search(r"<UCD_URL>(.*?)</UCD_URL>", response.text)
            html_match = re.search(r"<UCD_HTML>(.*?)</UCD_HTML>", response.text, re.DOTALL)
            logger.info(f"UCD_HTML match found: {bool(html_match)}")
            if html_match:
                logger.info(f"UCD_HTML content length: {len(html_match.group(1))}")
            sonuc_match = re.search(r"<Sonuc>(\d+)</Sonuc>", response.text)
            sonuc_str_match = re.search(r"<Sonuc_Str>(.*?)</Sonuc_Str>", response.text)
            
            if sonuc_match and int(sonuc_match.group(1)) > 0:
                if match and match.group(1):
                    return {
                        'success': True,
                        'payment_url': match.group(1),
                        'order_id': order_id,
                        'amount': amount,
                        'requires_redirect': True,
                        'message': '3D Secure sayfasına yönlendiriliyorsunuz'
                    }
                elif html_match and html_match.group(1):
                    # UCD_HTML döndü, form-based yönlendirme yap
                    return {
                        "success": True,
                        "html_content": html.unescape(html_match.group(1)),
                        "order_id": order_id,
                        "amount": amount,
                        "is_html_form": True,
                        "message": "3D Secure formuna yönlendiriliyorsunuz"
                    }
                else:
                    return {
                        'success': False,
                        'error': 'UCD_URL bulunamadı',
                        'order_id': order_id
                    }
            else:
                error_msg = sonuc_str_match.group(1) if sonuc_str_match else 'Bilinmeyen hata'
                return {
                    'success': False,
                    'error': f'Param Error: {error_msg}',
                    'order_id': order_id
                }
                
        except Exception as e:
            logger.error(f"Response parse error: {str(e)}")
            return {
                'success': False,
                'error': f'Response parse error: {str(e)}',
                'order_id': order_id
            }
    
    def create_form_based_payment(self, request, package_type, user_data=None):
        """Form-based ödeme (SOAP başarısız olunca fallback)"""
        try:
            current_site = get_current_site(request)
            
            # Order details
            order_id = f"LEX_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{request.user.id if hasattr(request, 'user') else ''}"
            amount_kurus = self.get_package_amount(package_type)
            amount_tl = amount_kurus / 100
            
            # URLs
            domain = current_site.domain
            if domain == 'example.com' or '145.223.82.130' in domain:
                domain = 'lexatech.ai'
            
            success_url = f"https://{domain}{reverse('payment_success')}"
            fail_url = f"https://{domain}{reverse('payment_fail')}"
            
            # Form parameters for Param Gateway
            import hmac
            hash_string = f"{self.client_code}{order_id}{amount_kurus}{self.password}"
            signature = hmac.new(
                self.password.encode('utf-8'),
                hash_string.encode('utf-8'),
                hashlib.sha256
            ).digest()
            hash_value = base64.b64encode(signature).decode('utf-8')
            
            # Form parameters
            form_params = {
                'CLIENT_CODE': self.client_code,
                'CLIENT_USERNAME': self.username,
                'GUID': self.guid,
                'MERCHANT_OID': order_id,
                'TOTAL_AMOUNT': amount_kurus,
                'CURRENCY': 'TL',
                'SUCCESS_URL': success_url,
                'FAIL_URL': fail_url,
                'HASH': hash_value,
                'INSTALLMENT_COUNT': '1',
                'TEST_MODE': '1' if self.test_mode else '0',
                'PRODUCT_NAME': self.get_package_description(package_type)
            }
            
            # Form URL
            if self.test_mode:
                form_url = 'https://test-dmz.param.com.tr/tr/param/ParamPayment.aspx'
            else:
                form_url = 'https://dmz.param.com.tr/tr/param/ParamPayment.aspx'
            
            logger.info(f"Form-based payment created - Order: {order_id}, Amount: {amount_tl} TL")
            
            return {
                'success': True,
                'payment_url': form_url,
                'form_params': form_params,
                'order_id': order_id,
                'amount': amount_tl,
                'is_form': True,
                'requires_redirect': True,
                'message': 'Form tabanlı ödeme sayfasına yönlendiriliyorsunuz'
            }
            
        except Exception as e:
            logger.error(f"Form-based payment error: {str(e)}")
            return {
                'success': False,
                'error': f'Form ödeme hazırlama hatası: {str(e)}',
                'order_id': order_id if 'order_id' in locals() else None
            }
    
    def complete_3d_payment(self, request, callback_data):
        """3D Secure sonrası ödemeyi tamamla - TP_WMD_Pay SOAP"""
        try:
            # 3D callback parametreleri
            ucd_md = callback_data.get('md', '')
            md_status = callback_data.get('mdStatus', '')
            islem_guid = callback_data.get('islemGUID', '')
            order_id = callback_data.get('orderId', '')
            
            logger.info(f"3D Callback - mdStatus: {md_status}, Order: {order_id}, GUID: {islem_guid[:20]}...")
            
            # mdStatus kontrolü (1,2,3,4 = success)
            if md_status not in ['1', '2', '3', '4']:
                return {
                    'success': False,
                    'error': f'3D doğrulama başarısız - mdStatus: {md_status}',
                    'order_id': order_id
                }
            
            # TP_WMD_Pay SOAP request
            soap_body = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
               xmlns:xsd="http://www.w3.org/2001/XMLSchema" 
               xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <TP_WMD_Pay xmlns="https://turkpos.com.tr/">
      <G>
        <CLIENT_CODE>{self.client_code}</CLIENT_CODE>
        <CLIENT_USERNAME>{self.username}</CLIENT_USERNAME>
        <CLIENT_PASSWORD>{self.password}</CLIENT_PASSWORD>
      </G>
      <GUID>{self.guid.lower()}</GUID>
      <UCD_MD>{ucd_md}</UCD_MD>
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
            
            logger.info(f"Sending TP_WMD_Pay request for order: {order_id}")
            
            response = requests.post(
                self.soap_url,
                data=soap_body.encode('utf-8'),
                headers=headers,
                timeout=30
            )
            
            logger.info(f"TP_WMD_Pay response status: {response.status_code}")
            logger.info(f"TP_WMD_Pay response: {response.text}")
            
            if response.status_code == 200:
                # Parse response
                sonuc_match = re.search(r"<Sonuc>(\d+)</Sonuc>", response.text)
                dekont_match = re.search(r"<Dekont_ID>(\d+)</Dekont_ID>", response.text)
                sonuc_str_match = re.search(r"<Sonuc_Str>(.*?)</Sonuc_Str>", response.text)
                
                if sonuc_match and int(sonuc_match.group(1)) > 0 and dekont_match and int(dekont_match.group(1)) > 0:
                    return {
                        'success': True,
                        'order_id': order_id,
                        'transaction_id': dekont_match.group(1),
                        'dekont_id': dekont_match.group(1),
                        'message': sonuc_str_match.group(1) if sonuc_str_match else 'Ödeme başarıyla tamamlandı'
                    }
                else:
                    error_code = sonuc_match.group(1) if sonuc_match else 'Unknown'
                    error_msg = sonuc_str_match.group(1) if sonuc_str_match else 'Ödeme tamamlanamadı'
                    return {
                        'success': False,
                        'error': f'Payment completion failed ({error_code}): {error_msg}',
                        'order_id': order_id
                    }
            else:
                return {
                    'success': False,
                    'error': f'TP_WMD_Pay HTTP error: {response.status_code}',
                    'order_id': order_id
                }
                
        except Exception as e:
            logger.error(f"3D payment completion error: {str(e)}")
            return {
                'success': False,
                'error': f'3D ödeme tamamlama hatası: {str(e)}',
                'order_id': order_id if 'order_id' in locals() else None
            }
    
    def create_demo_payment(self, request, package_type):
        """Demo ödeme akışı"""
        current_site = get_current_site(request)
        order_id = f"DEMO_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        amount = self.get_package_amount(package_type) / 100
        
        demo_url = f"http://{current_site.domain}/demo-payment/?order_id={order_id}&amount={amount}&package={package_type}"
        
        return {
            'success': True,
            'payment_url': demo_url,
            'order_id': order_id,
            'amount': amount,
            'is_demo': True,
            'requires_redirect': True,
            'message': 'Demo ödeme sayfası'
        }
    
    def get_client_ip(self, request):
        """İstemci IP adresini al"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip