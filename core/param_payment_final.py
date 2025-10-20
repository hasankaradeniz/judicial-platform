# param_payment_final.py - Gerçek Credentials ile Test/Production Ödeme Servisi

import hashlib
import base64
from datetime import datetime
from django.conf import settings
from django.urls import reverse
from django.contrib.sites.shortcuts import get_current_site
import logging
import requests
from lxml import etree

logger = logging.getLogger(__name__)

class ParamPaymentService:
    def __init__(self):
        # Gerçek credentials
        self.client_code = "145942"
        self.guid = "E204D733-02BA-4312-B03F-84BFE184313C"
        self.client_username = "TP10173244"
        self.client_password = "E78A466F0083A439"
        
        # Test modunu settings'den al veya default True
        self.test_mode = getattr(settings, 'PARAM_TEST_MODE', True)
        
        # URL'ler
        if self.test_mode:
            self.soap_url = "https://testposws.param.com.tr/turkpos.ws/service_turkpos_prod.asmx"
        else:
            self.soap_url = "https://posws.param.com.tr/turkpos.ws/service_turkpos_prod.asmx"
            
        logger.info(f"ParamPaymentService initialized - Test Mode: {self.test_mode}")
        
    def sha2b64(self, data):
        """SHA256 + Base64 hash hesaplama"""
        hash_bytes = hashlib.sha256(data.encode('utf-8')).digest()
        return base64.b64encode(hash_bytes).decode('utf-8')
    
    def get_package_amount(self, package_type):
        """Paket tutarları"""
        if self.test_mode:
            # Test için düşük tutarlar
            amounts = {
                'monthly': 1.00,
                'quarterly': 2.50,
                'semi_annual': 4.50,
                'annual': 10.00
            }
        else:
            # Gerçek tutarlar
            amounts = {
                'monthly': 1000.00,
                'quarterly': 2500.00,
                'semi_annual': 4500.00,
                'annual': 10000.00
            }
        return amounts.get(package_type, 1.00 if self.test_mode else 1000.00)
    
    def start_payment(self, request, package_type, user_data):
        """Kart bilgileri formu göster"""
        amount = self.get_package_amount(package_type)
        
        # Kart bilgileri form sayfasına yönlendir
        request.session['pending_payment'] = {
            'package_type': package_type,
            'amount': amount,
            'user_data': user_data
        }
        
        return {
            'success': True,
            'show_card_form': True,
            'amount': amount,
            'package_type': package_type
        }
    
    def process_payment(self, request, card_data, payment_data):
        """Kart bilgileriyle ödemeyi işle"""
        try:
            # Parametreler
            amount = payment_data['amount']
            package_type = payment_data['package_type']
            amount_str = f"{amount:.2f}".replace('.', ',')  # Virgüllü format
            
            # Sipariş ID
            order_id = f"{'TEST' if self.test_mode else 'LEX'}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # URL'ler
            current_site = get_current_site(request)
            domain = current_site.domain
            if 'lexatech.ai' not in domain:
                domain = 'lexatech.ai'
            
            success_url = f"https://{domain}/payment/success/"
            fail_url = f"https://{domain}/payment/fail/"
            
            # Hash hesaplama
            taksit = "1"
            hash_string = f"{self.client_code}{self.guid}{taksit}{amount_str}{amount_str}{order_id}{fail_url}{success_url}"
            islem_hash = self.sha2b64(hash_string)
            
            logger.info(f"Payment Processing Debug:")
            logger.info(f"  Mode: {'TEST' if self.test_mode else 'PRODUCTION'}")
            logger.info(f"  Amount: {amount_str}")
            logger.info(f"  Order ID: {order_id}")
            logger.info(f"  Card Number (masked): {'*' * 12}{card_data['card_number'][-4:]}")
            
            # SOAP XML
            soap_body = f'''<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
               xmlns:xsd="http://www.w3.org/2001/XMLSchema" 
               xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <Pos_Odeme xmlns="https://turkpos.com.tr/">
      <G>
        <CLIENT_CODE>{self.client_code}</CLIENT_CODE>
        <CLIENT_USERNAME>{self.client_username}</CLIENT_USERNAME>
        <CLIENT_PASSWORD>{self.client_password}</CLIENT_PASSWORD>
      </G>
      <GUID>{self.guid}</GUID>
      <KK_Sahibi>{card_data['card_holder']}</KK_Sahibi>
      <KK_No>{card_data['card_number']}</KK_No>
      <KK_SK_Ay>{card_data['exp_month']}</KK_SK_Ay>
      <KK_SK_Yil>{card_data['exp_year']}</KK_SK_Yil>
      <KK_CVC>{card_data['cvv']}</KK_CVC>
      <KK_Sahibi_GSM>{card_data['gsm']}</KK_Sahibi_GSM>
      <Hata_URL>{fail_url}</Hata_URL>
      <Basarili_URL>{success_url}</Basarili_URL>
      <Siparis_ID>{order_id}</Siparis_ID>
      <Siparis_Aciklama>Lexatech {package_type} Abonelik</Siparis_Aciklama>
      <Taksit>{taksit}</Taksit>
      <Islem_Tutar>{amount_str}</Islem_Tutar>
      <Toplam_Tutar>{amount_str}</Toplam_Tutar>
      <Islem_Hash>{islem_hash}</Islem_Hash>
      <Islem_Guvenlik_Tip>3D</Islem_Guvenlik_Tip>
      <Islem_ID></Islem_ID>
      <IPAdr>{request.META.get('REMOTE_ADDR', '0.0.0.0')}</IPAdr>
      <Ref_URL>{request.build_absolute_uri()}</Ref_URL>
      <Data1></Data1>
      <Data2></Data2>
      <Data3></Data3>
      <Data4></Data4>
      <Data5></Data5>
    </Pos_Odeme>
  </soap:Body>
</soap:Envelope>'''

            # SOAP isteği
            headers = {
                'Content-Type': 'text/xml; charset=utf-8',
                'SOAPAction': 'https://turkpos.com.tr/Pos_Odeme'
            }
            
            logger.info(f"Sending SOAP request to: {self.soap_url}")
            logger.info(f"SOAP Headers: {headers}")
            logger.debug(f"SOAP Body: {soap_body[:500]}...")
            
            response = requests.post(self.soap_url, data=soap_body, headers=headers, timeout=30)
            
            logger.info(f"SOAP Response Status: {response.status_code}")
            logger.info(f"SOAP Response Headers: {response.headers}")
            logger.debug(f"SOAP Response Body: {response.text[:1000]}...")
            
            if response.status_code == 200:
                # Parse response
                root = etree.fromstring(response.content)
                ns = {'soap': 'http://schemas.xmlsoap.org/soap/envelope/', 
                      'ns': 'https://turkpos.com.tr/'}
                
                result = root.find('.//ns:Pos_OdemeResult', ns)
                if result is not None:
                    sonuc = result.find('.//ns:Sonuc', ns)
                    sonuc_str = result.find('.//ns:Sonuc_Str', ns)
                    ucd_url = result.find('.//ns:UCD_URL', ns)
                    islem_id = result.find('.//ns:Islem_ID', ns)
                    
                    if sonuc is not None and int(sonuc.text) > 0 and ucd_url is not None:
                        # Save payment info to session
                        request.session['payment_info'] = {
                            'order_id': order_id,
                            'islem_id': islem_id.text if islem_id is not None else '',
                            'package_type': package_type,
                            'amount': amount
                        }
                        
                        return {
                            'success': True,
                            'payment_url': ucd_url.text,
                            'requires_redirect': True
                        }
                    else:
                        error_msg = sonuc_str.text if sonuc_str is not None else 'Bilinmeyen hata'
                        return {
                            'success': False,
                            'error': f'Param: {error_msg}'
                        }
                else:
                    return {
                        'success': False,
                        'error': 'SOAP yanıtı ayrıştırılamadı'
                    }
            else:
                logger.error(f"SOAP Error - Status: {response.status_code}")
                logger.error(f"SOAP Error - Response: {response.text}")
                return {
                    'success': False,
                    'error': f'SOAP isteği başarısız: {response.status_code} - {response.text[:200]}'
                }
                
        except Exception as e:
            logger.error(f"Payment processing error: {str(e)}", exc_info=True)
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                'success': False,
                'error': f'Ödeme işleme hatası: {str(e)}'
            }
    
    def get_package_description(self, package_type):
        """Paket açıklamaları"""
        descriptions = {
            'monthly': 'Aylık Abonelik',
            'quarterly': '3 Aylık Abonelik',
            'semi_annual': '6 Aylık Abonelik',
            'annual': 'Yıllık Abonelik'
        }
        prefix = 'Test ' if self.test_mode else 'Lexatech '
        return prefix + descriptions.get(package_type, 'Abonelik')
