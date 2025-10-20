# param_payment_test.py - Param Test Ortamı Ödeme Servisi

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

class TestParamPayment:
    def __init__(self):
        # Test ortamı credentials - dokümantasyondan
        self.client_code = "10738"  # Test client code
        self.guid = "0c13d406-873b-403b-9c09-a5766840d98c"  # Test GUID
        self.client_username = "Test"
        self.client_password = "Test"
        
        # Test SOAP Endpoint
        self.soap_url = "https://testposws.param.com.tr/turkpos.ws/service_turkpos_prod.asmx"
        
    def sha2b64(self, data):
        """SHA256 + Base64 hash hesaplama"""
        hash_bytes = hashlib.sha256(data.encode('utf-8')).digest()
        return base64.b64encode(hash_bytes).decode('utf-8')
    
    def get_package_amount(self, package_type):
        """Test için düşük tutarlar"""
        amounts = {
            'monthly': 1.00,      # 1.00 TL test
            'quarterly': 2.50,    # 2.50 TL test
            'semi_annual': 4.50,  # 4.50 TL test
            'annual': 10.00       # 10.00 TL test
        }
        return amounts.get(package_type, 1.00)
    
    def create_payment(self, request, package_type):
        """Test ortamında 3D ödeme başlat"""
        try:
            # Temel parametreler
            amount = self.get_package_amount(package_type)
            amount_str = f"{amount:.2f}".replace('.', ',')  # Virgüllü format: 1,00
            
            # Sipariş ID 
            order_id = f"TEST_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # URL'ler
            current_site = get_current_site(request)
            domain = current_site.domain
            if 'lexatech.ai' not in domain:
                domain = 'lexatech.ai'
            
            success_url = f"https://{domain}/payment/success/"
            fail_url = f"https://{domain}/payment/fail/"
            
            # Hash hesaplama - Dokümantasyona göre
            taksit = "1"
            hash_string = f"{self.client_code}{self.guid}{taksit}{amount_str}{amount_str}{order_id}{fail_url}{success_url}"
            islem_hash = self.sha2b64(hash_string)
            
            logger.info(f"Test Payment Debug:")
            logger.info(f"  Client Code: {self.client_code}")
            logger.info(f"  GUID: {self.guid}")
            logger.info(f"  Amount: {amount_str}")
            logger.info(f"  Order ID: {order_id}")
            logger.info(f"  Hash String: {hash_string}")
            logger.info(f"  Hash Value: {islem_hash}")
            
            # Test kart bilgileri
            test_card = {
                'number': '4444444444444444',
                'holder': 'TEST USER',
                'month': '12',
                'year': '2026',
                'cvv': '000',
                'gsm': '5555555555'
            }
            
            # SOAP XML oluştur
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
      <KK_Sahibi>{test_card['holder']}</KK_Sahibi>
      <KK_No>{test_card['number']}</KK_No>
      <KK_SK_Ay>{test_card['month']}</KK_SK_Ay>
      <KK_SK_Yil>{test_card['year']}</KK_SK_Yil>
      <KK_CVC>{test_card['cvv']}</KK_CVC>
      <KK_Sahibi_GSM>{test_card['gsm']}</KK_Sahibi_GSM>
      <Hata_URL>{fail_url}</Hata_URL>
      <Basarili_URL>{success_url}</Basarili_URL>
      <Siparis_ID>{order_id}</Siparis_ID>
      <Siparis_Aciklama>Test Lexatech {package_type} Abonelik</Siparis_Aciklama>
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

            logger.info(f"Sending SOAP request to: {self.soap_url}")
            
            # SOAP isteği gönder
            headers = {
                'Content-Type': 'text/xml; charset=utf-8',
                'SOAPAction': 'https://turkpos.com.tr/Pos_Odeme'
            }
            
            response = requests.post(self.soap_url, data=soap_body, headers=headers, timeout=30)
            logger.info(f"SOAP Response Status: {response.status_code}")
            logger.info(f"SOAP Response: {response.text[:500]}...")
            
            if response.status_code == 200:
                # Parse SOAP response
                root = etree.fromstring(response.content)
                ns = {'soap': 'http://schemas.xmlsoap.org/soap/envelope/', 
                      'ns': 'https://turkpos.com.tr/'}
                
                result = root.find('.//ns:Pos_OdemeResult', ns)
                if result is not None:
                    sonuc = result.find('.//ns:Sonuc', ns)
                    sonuc_str = result.find('.//ns:Sonuc_Str', ns)
                    ucd_url = result.find('.//ns:UCD_URL', ns)
                    islem_id = result.find('.//ns:Islem_ID', ns)
                    
                    logger.info(f"Sonuc: {sonuc.text if sonuc is not None else 'None'}")
                    logger.info(f"Sonuc_Str: {sonuc_str.text if sonuc_str is not None else 'None'}")
                    logger.info(f"UCD_URL: {ucd_url.text if ucd_url is not None else 'None'}")
                    
                    if sonuc is not None and int(sonuc.text) > 0 and ucd_url is not None:
                        # 3D URL'ye yönlendir
                        return {
                            'success': True,
                            'payment_url': ucd_url.text,
                            'order_id': order_id,
                            'islem_id': islem_id.text if islem_id is not None else '',
                            'requires_redirect': True,
                            'is_form': False,
                            'message': 'Test ortamında 3D güvenli ödeme başlatıldı'
                        }
                    else:
                        error_msg = sonuc_str.text if sonuc_str is not None else 'Bilinmeyen hata'
                        return {
                            'success': False,
                            'error': f'Test Param hatası: {error_msg}'
                        }
                else:
                    return {
                        'success': False,
                        'error': 'SOAP yanıtı ayrıştırılamadı'
                    }
            else:
                return {
                    'success': False,
                    'error': f'SOAP isteği başarısız: {response.status_code}'
                }
                
        except Exception as e:
            logger.error(f"Test payment error: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f'Test ödeme hatası: {str(e)}'
            }
    
    def get_package_description(self, package_type):
        """Paket açıklamalarını döndür"""
        descriptions = {
            'monthly': 'Test Aylık Abonelik',
            'quarterly': 'Test 3 Aylık Abonelik',
            'semi_annual': 'Test 6 Aylık Abonelik',
            'annual': 'Test Yıllık Abonelik'
        }
        return descriptions.get(package_type, 'Test Abonelik')
