"""
Param Ortak Ödeme Sayfası (TO_Pre_Encrypting_OOS) Servisi
Bu servis daha basit ve güvenilir ödeme akışı sağlar
"""

import requests
import logging
from datetime import datetime
from django.conf import settings
from django.urls import reverse
from django.contrib.sites.shortcuts import get_current_site

logger = logging.getLogger(__name__)

class ParamSharedPaymentService:
    """Param Ortak Ödeme Sayfası servisi"""
    
    def __init__(self):
        # Test/Production mode
        self.test_mode = getattr(settings, 'PARAM_TEST_MODE', True)
        
        if self.test_mode:
            # Test credentials
            self.client_code = '10738'
            self.username = 'Test'
            self.password = 'Test'
            self.guid = '0C13D406-873B-403B-9C09-A5766840D98C'
            self.terminal_id = '10738'
            self.soap_url = 'https://testposws.param.com.tr/Turkpos.ws/service_turkpos_prod.asmx'
            self.payment_base_url = 'https://testpos.param.com.tr/Tahsilat/Default.aspx?s='
        else:
            # Production credentials
            self.client_code = getattr(settings, 'PARAM_CLIENT_CODE', '145942')
            self.username = getattr(settings, 'PARAM_CLIENT_USERNAME', 'TP10173244')
            self.password = getattr(settings, 'PARAM_CLIENT_PASSWORD', 'E78A466F0083A439')
            self.guid = getattr(settings, 'PARAM_GUID', 'E204D733-02BA-4312-B03F-84BFE184313C')
            self.terminal_id = self.client_code
            self.soap_url = 'https://posws.param.com.tr/Turkpos.ws/service_turkpos_prod.asmx'
            self.payment_base_url = 'https://pos.param.com.tr/Tahsilat/Default.aspx?s='
    
    def get_package_amount(self, package_type):
        """Paket fiyatları (TL cinsinden, virgül ile)"""
        prices = {
            'monthly': '1000,00',
            'quarterly': '2700,00', 
            'semi_annual': '5200,00',
            'annual': '10000,00',
        }
        return prices.get(package_type, '1000,00')
    
    def get_package_description(self, package_type):
        """Paket açıklamaları"""
        descriptions = {
            'monthly': 'Lexatech Aylik Abonelik',
            'quarterly': 'Lexatech 3 Aylik Abonelik',
            'semi_annual': 'Lexatech 6 Aylik Abonelik',
            'annual': 'Lexatech Yillik Abonelik',
        }
        return descriptions.get(package_type, 'Lexatech Abonelik')
    
    def create_shared_payment(self, request, package_type, user_data):
        """TO_Pre_Encrypting_OOS ile ortak ödeme sayfası oluştur"""
        try:
            current_site = get_current_site(request)
            
            # Order details
            order_id = f"LEX_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{request.user.id}"
            amount_str = self.get_package_amount(package_type)
            
            # URLs
            domain = current_site.domain
            if domain == 'example.com' or '145.223.82.130' in domain:
                domain = 'lexatech.ai'
            
            return_url = f"https://{domain}/payment/success/"
            
            # Customer data
            customer_name = user_data.get('customer_name', 'Test Customer')
            customer_phone = user_data.get('customer_phone', '5555555555')
            
            # SOAP XML for TO_Pre_Encrypting_OOS
            soap_body = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
               xmlns:xsd="http://www.w3.org/2001/XMLSchema" 
               xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <TO_Pre_Encrypting_OOS xmlns="https://turkodeme.com.tr/">
      <G>
        <CLIENT_CODE>{self.client_code}</CLIENT_CODE>
        <CLIENT_USERNAME>{self.username}</CLIENT_USERNAME>
        <CLIENT_PASSWORD>{self.password}</CLIENT_PASSWORD>
      </G>
      <GUID>{self.guid}</GUID>
      <Borclu_Kisi_TC></Borclu_Kisi_TC>
      <Borclu_Aciklama>r|{self.get_package_description(package_type)}</Borclu_Aciklama>
      <Borclu_Tutar>r|{amount_str}</Borclu_Tutar>
      <Borclu_GSM>r|{customer_phone}</Borclu_GSM>
      <Borclu_Odeme_Tip>r|Diğer</Borclu_Odeme_Tip>
      <Borclu_AdSoyad>{customer_name}</Borclu_AdSoyad>
      <Return_URL>{return_url}</Return_URL>
      <Islem_ID>{order_id}</Islem_ID>
      <Terminal_ID>{self.terminal_id}</Terminal_ID>
      <Taksit>1</Taksit>
    </TO_Pre_Encrypting_OOS>
  </soap:Body>
</soap:Envelope>"""
            
            # SOAP headers
            headers = {
                'Content-Type': 'text/xml; charset=utf-8',
                'SOAPAction': 'https://turkodeme.com.tr/TO_Pre_Encrypting_OOS',
                'Accept': 'text/xml'
            }
            
            logger.info(f"Sending TO_Pre_Encrypting_OOS request - Order: {order_id}, Amount: {amount_str} TL")
            
            response = requests.post(
                self.soap_url,
                data=soap_body.encode('utf-8'),
                headers=headers,
                timeout=30,
                verify=True
            )
            
            if response.status_code == 200:
                return self.parse_shared_payment_response(response, order_id, amount_str)
            else:
                logger.error(f"Shared payment request failed: {response.status_code}")
                return {
                    'success': False,
                    'error': f'HTTP {response.status_code}: {response.text}',
                    'order_id': order_id
                }
                
        except Exception as e:
            logger.error(f"Shared payment error: {str(e)}")
            return {
                'success': False,
                'error': f'Shared payment error: {str(e)}',
                'order_id': order_id if 'order_id' in locals() else None
            }
    
    def parse_shared_payment_response(self, response, order_id, amount):
        """TO_Pre_Encrypting_OOS response parse et"""
        try:
            logger.info(f"TO_Pre_Encrypting_OOS Response: {response.text}")
            
            # Parse XML response for encrypted string
            import re
            result_match = re.search(r'<TO_Pre_Encrypting_OOSResult[^>]*>(.*?)</TO_Pre_Encrypting_OOSResult>', response.text, re.DOTALL)
            
            if result_match and result_match.group(1).strip():
                encrypted_string = result_match.group(1).strip()
                payment_url = f"{self.payment_base_url}{encrypted_string}"
                
                return {
                    'success': True,
                    'payment_url': payment_url,
                    'order_id': order_id,
                    'amount': amount,
                    'requires_redirect': True,
                    'message': 'Ortak ödeme sayfasına yönlendiriliyorsunuz'
                }
            else:
                return {
                    'success': False,
                    'error': 'Encrypted payment string bulunamadı',
                    'order_id': order_id
                }
                
        except Exception as e:
            logger.error(f"Response parse error: {str(e)}")
            return {
                'success': False,
                'error': f'Response parse error: {str(e)}',
                'order_id': order_id
            }
