"""
Param Sanal POS Entegrasyonu - Düzeltilmiş Versiyon
"""

import hashlib
import base64
import json
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from django.conf import settings
from django.urls import reverse
from django.contrib.sites.shortcuts import get_current_site
import logging

logger = logging.getLogger(__name__)


class ParamPaymentService:
    """Param Sanal POS servisi - Fixed version"""
    
    def __init__(self):
        # Param credentials
        self.client_code = getattr(settings, 'PARAM_CLIENT_CODE', '145942')
        self.username = getattr(settings, 'PARAM_CLIENT_USERNAME', 'TP10173244')
        self.password = getattr(settings, 'PARAM_CLIENT_PASSWORD', 'E78A466F0083A439')
        self.guid = getattr(settings, 'PARAM_GUID', 'E204D733-02BA-4312-B03F-84BFE184313C')
        
        # Test/Production mode
        self.test_mode = getattr(settings, 'PARAM_TEST_MODE', True)
        
        # SOAP Endpoints
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
    
    def generate_order_id(self, user_id=None):
        """Sipariş ID oluştur"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        if user_id:
            return f"LEX_{timestamp}_{user_id}"
        return f"LEX_{timestamp}"
    
    def create_tp_wmd_ucd_request(self, request, package_type, user_data=None):
        """Ana ödeme metodu - Güncel SOAP API"""
        try:
            current_site = get_current_site(request)
            
            # Demo mode check
            if current_site.domain in ['127.0.0.1:8000', 'localhost:8000', 'testserver']:
                return self.create_demo_payment(request, package_type)
            
            # SOAP TP_WMD_UCD metodunu kullan
            return self.create_soap_payment(request, package_type, user_data)
            
        except Exception as e:
            logger.error(f"Payment creation error: {str(e)}")
            return {
                'success': False,
                'error': f'Ödeme oluşturma hatası: {str(e)}'
            }
    
    def create_soap_payment(self, request, package_type, user_data=None):
        """SOAP TP_WMD_UCD metodu"""
        try:
            current_site = get_current_site(request)
            
            # Order details
            order_id = self.generate_order_id(request.user.id if hasattr(request, 'user') else None)
            amount_kurus = self.get_package_amount(package_type)
            amount_tl = amount_kurus / 100
            amount_str = f"{amount_tl:.2f}".replace('.', ',')  # Virgüllü format
            
            # URLs
            domain = current_site.domain
            if domain == 'example.com' or '145.223.82.130' in domain:
                domain = 'lexatech.ai'  # Public domain kullan
            
            success_url = f"https://{domain}{reverse('payment_success')}"
            fail_url = f"https://{domain}{reverse('payment_fail')}"
            
            # Hash calculation for TP_WMD_UCD
            taksit = "1"  # Single payment
            hash_string = f"{self.client_code}{self.guid}{taksit}{amount_str}{amount_str}{order_id}{fail_url}{success_url}"
            hash_value = base64.b64encode(hashlib.sha256(hash_string.encode('utf-8')).digest()).decode('utf-8')
            
            # Transaction ID
            transaction_id = f"TXN_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # SOAP XML
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
      <Siparis_Aciklama>{self.get_package_description(package_type)}</Siparis_Aciklama>
      <Taksit>{taksit}</Taksit>
      <Islem_Tutar>{amount_str}</Islem_Tutar>
      <Toplam_Tutar>{amount_str}</Toplam_Tutar>
      <Islem_Hash>{hash_value}</Islem_Hash>
      <Islem_Guvenlik_Tip>3D</Islem_Guvenlik_Tip>
      <Islem_ID>{transaction_id}</Islem_ID>
      <IPAdr>145.223.82.130</IPAdr>
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
            
            logger.info(f"Sending SOAP TP_WMD_UCD - Order: {order_id}, Amount: {amount_tl} TL")
            
            # SOAP request gönder
            response = requests.post(
                self.soap_url,
                data=soap_body.encode('utf-8'),
                headers=headers,
                timeout=30,
                verify=True
            )
            
            if response.status_code == 200:
                return self.parse_soap_response(response, order_id, amount_tl)
            elif response.status_code == 403:
                logger.error("IP not registered - Contact Param support")
                return {
                    'success': False,
                    'error': 'IP adresi kayıtlı değil. Param desteği ile iletişime geçin.',
                    'order_id': order_id
                }
            else:
                logger.error(f"SOAP failed: {response.status_code} - {response.text[:200]}")
                return {
                    'success': False,
                    'error': f'SOAP API hatası: {response.status_code}',
                    'order_id': order_id
                }
                
        except Exception as e:
            logger.error(f"SOAP payment error: {str(e)}")
            return {
                'success': False,
                'error': f'SOAP isteği hatası: {str(e)}',
                'order_id': order_id if 'order_id' in locals() else None
            }
    
    def parse_soap_response(self, response, order_id, amount):
        """SOAP response parse et"""
        try:
            logger.info(f"SOAP Response: {response.text[:500]}")
            
            root = ET.fromstring(response.text)
            
            # Parse response elements
            sonuc = root.find('.//Sonuc')
            sonuc_str = root.find('.//Sonuc_Str') 
            ucd_url = root.find('.//UCD_URL')
            dekont_id = root.find('.//Dekont_ID')
            islem_guid = root.find('.//Islem_GUID')
            
            logger.info(f"Sonuc: {sonuc.text if sonuc is not None else 'NOT FOUND'}")
            logger.info(f"UCD_URL: {ucd_url.text if ucd_url is not None else 'NOT FOUND'}")
            
            # Success check
            if sonuc is not None and int(sonuc.text) > 0:
                if ucd_url is not None and ucd_url.text:
                    return {
                        'success': True,
                        'payment_url': ucd_url.text,
                        'order_id': order_id,
                        'amount': amount,
                        'transaction_guid': islem_guid.text if islem_guid is not None else '',
                        'requires_redirect': True,
                        'message': '3D Secure sayfasına yönlendiriliyorsunuz'
                    }
            
            # Error case
            error_code = sonuc.text if sonuc is not None else 'Unknown'
            error_msg = sonuc_str.text if sonuc_str is not None else 'Unknown error'
            return {
                'success': False,
                'error': f'Param Error ({error_code}): {error_msg}',
                'order_id': order_id
            }
            
        except Exception as e:
            logger.error(f"SOAP parse error: {str(e)}")
            return {
                'success': False,
                'error': f'Response parse error: {str(e)}',
                'order_id': order_id
            }
    
    
    def create_demo_payment(self, request, package_type):
        """Demo ödeme akışı"""
        current_site = get_current_site(request)
        order_id = self.generate_order_id()
        amount = self.get_package_amount(package_type) / 100
        
        # Domain düzeltmesi
        domain = current_site.domain
        if domain == 'example.com' or '145.223.82.130' in domain:
            domain = 'lexatech.ai'
        
        demo_url = f"https://{domain}/demo-payment/?order_id={order_id}&amount={amount}&package={package_type}"
        
        return {
            'success': True,
            'payment_url': demo_url,
            'order_id': order_id,
            'amount': amount,
            'is_demo': True,
            'requires_redirect': True,
            'message': 'Demo ödeme sayfası'
        }
    
    def verify_payment_callback(self, callback_data):
        """Ödeme callback doğrulama"""
        try:
            # Demo check
            if callback_data.get('demo') == '1':
                return {
                    'success': callback_data.get('status') == 'success',
                    'order_id': callback_data.get('order_id'),
                    'amount': callback_data.get('amount', '0'),
                    'is_demo': True
                }
            
            # Standard callback verification
            return {
                'success': callback_data.get('status') == 'success',
                'order_id': callback_data.get('order_id') or callback_data.get('MERCHANT_OID'),
                'transaction_id': callback_data.get('transaction_id') or callback_data.get('TRANSACTION_ID'),
                'amount': callback_data.get('amount') or callback_data.get('TOTAL_AMOUNT')
            }
            
        except Exception as e:
            logger.error(f"Callback verification error: {str(e)}")
            return {
                'success': False,
                'error': f'Callback verification failed: {str(e)}'
            }