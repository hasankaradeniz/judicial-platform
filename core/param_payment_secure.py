# param_payment_secure.py - Param Dokümantasyonuna Uygun Güvenli Ödeme Servisi

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

class SecureParamPayment:
    def __init__(self):
        # Param Production Credentials
        self.client_code = "145942"
        self.guid = "E204D733-02BA-4312-B03F-84BFE184313C"
        self.client_username = "TP10173244"
        self.client_password = "E78A466F0083A439"
        
        # SOAP Endpoint
        self.soap_url = "https://posws.param.com.tr/turkpos.ws/service_turkpos_prod.asmx"
        
    def sha2b64(self, data):
        """SHA256 + Base64 hash hesaplama"""
        hash_bytes = hashlib.sha256(data.encode('utf-8')).digest()
        return base64.b64encode(hash_bytes).decode('utf-8')
    
    def get_package_amount(self, package_type):
        """Paket tutarlarını döndür"""
        amounts = {
            'monthly': 1000.00,      # 1000.00 TL
            'quarterly': 2500.00,    # 2500.00 TL  
            'semi_annual': 4500.00,  # 4500.00 TL
            'annual': 10000.00       # 10000.00 TL
        }
        return amounts.get(package_type, 1000.00)
    
    def create_payment(self, request, package_type):
        """Param dokümantasyonuna göre Pos_Odeme metodu ile 3D ödeme başlat"""
        try:
            # Temel parametreler
            amount = self.get_package_amount(package_type)
            amount_str = f"{amount:.2f}".replace('.', ',')  # Virgüllü format: 1000,00
            
            # Sipariş ID 
            order_id = f"LEX_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # URL'ler
            current_site = get_current_site(request)
            domain = current_site.domain
            if 'lexatech.ai' not in domain:
                domain = 'lexatech.ai'
            
            success_url = f"https://{domain}/payment/success/"
            fail_url = f"https://{domain}/payment/fail/"
            
            # Hash hesaplama - Dokümantasyona göre
            # CLIENT_CODE & GUID & Taksit & Islem_Tutar & Toplam_Tutar & Siparis_ID & Hata_URL & Basarili_URL
            taksit = "1"
            hash_string = f"{self.client_code}{self.guid}{taksit}{amount_str}{amount_str}{order_id}{fail_url}{success_url}"
            islem_hash = self.sha2b64(hash_string)
            
            logger.info(f"Secure Payment Debug:")
            logger.info(f"  Hash String: {hash_string}")
            logger.info(f"  Hash Value: {islem_hash}")
            
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
      <KK_Sahibi>Test User</KK_Sahibi>
      <KK_No>4444444444444444</KK_No>
      <KK_SK_Ay>12</KK_SK_Ay>
      <KK_SK_Yil>2025</KK_SK_Yil>
      <KK_CVC>000</KK_CVC>
      <KK_Sahibi_GSM>5555555555</KK_Sahibi_GSM>
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

            # SOAP isteği gönder
            headers = {
                'Content-Type': 'text/xml; charset=utf-8',
                'SOAPAction': 'https://turkpos.com.tr/Pos_Odeme'
            }
            
            response = requests.post(self.soap_url, data=soap_body, headers=headers, timeout=30)
            logger.info(f"SOAP Response Status: {response.status_code}")
            
            if response.status_code == 200:
                # Parse SOAP response
                root = etree.fromstring(response.content)
                ns = {'soap': 'http://schemas.xmlsoap.org/soap/envelope/', 
                      'ns': 'https://turkpos.com.tr/'}
                
                sonuc = root.find('.//ns:Sonuc', ns)
                sonuc_str = root.find('.//ns:Sonuc_Str', ns)
                ucd_url = root.find('.//ns:UCD_URL', ns)
                islem_id = root.find('.//ns:Islem_ID', ns)
                
                if sonuc is not None and int(sonuc.text) > 0 and ucd_url is not None:
                    # 3D URL'ye yönlendir
                    return {
                        'success': True,
                        'payment_url': ucd_url.text,
                        'order_id': order_id,
                        'islem_id': islem_id.text if islem_id is not None else '',
                        'requires_redirect': True,
                        'is_form': False
                    }
                else:
                    error_msg = sonuc_str.text if sonuc_str is not None else 'Bilinmeyen hata'
                    return {
                        'success': False,
                        'error': f'Param hatası: {error_msg}'
                    }
            else:
                return {
                    'success': False,
                    'error': f'SOAP isteği başarısız: {response.status_code}'
                }
                
        except Exception as e:
            logger.error(f"Payment creation error: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f'Ödeme oluşturma hatası: {str(e)}'
            }
    
    def get_package_description(self, package_type):
        """Paket açıklamalarını döndür"""
        descriptions = {
            'monthly': 'Lexatech Aylık Abonelik',
            'quarterly': 'Lexatech 3 Aylık Abonelik',
            'semi_annual': 'Lexatech 6 Aylık Abonelik',
            'annual': 'Lexatech Yıllık Abonelik'
        }
        return descriptions.get(package_type, 'Lexatech Abonelik')
