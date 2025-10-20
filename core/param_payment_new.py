# param_payment_new.py - Sıfırdan Basit Param Ödeme Servisi

import hashlib
import base64
import uuid
from datetime import datetime
from django.conf import settings
from django.urls import reverse
from django.contrib.sites.shortcuts import get_current_site
import logging

logger = logging.getLogger(__name__)

class SimpleParamPayment:
    def __init__(self):
        # Param Production Credentials
        self.client_code = "145942"
        self.guid = "E204D733-02BA-4312-B03F-84BFE184313C"
        self.client_username = "TP10173244"
        self.client_password = "E78A466F0083A439"
        
        # Production URLs
        self.form_url = "https://dmz.param.com.tr/tr/param/ParamPayment.aspx"
        
    def calculate_hash(self, data_string):
        """SHA256 + Base64 hash hesaplama"""
        hash_bytes = hashlib.sha256(data_string.encode('utf-8')).digest()
        return base64.b64encode(hash_bytes).decode('utf-8')
    
    def get_package_amount(self, package_type):
        """Paket tutarlarını kuruş olarak döndür"""
        amounts = {
            'monthly': 100000,      # 1000.00 TL
            'quarterly': 250000,    # 2500.00 TL  
            'semi_annual': 450000,  # 4500.00 TL
            'annual': 800000        # 8000.00 TL
        }
        return amounts.get(package_type, 100000)
    
    def create_payment(self, request, package_type):
        """Basit form-based ödeme oluştur"""
        try:
            # Temel parametreler
            amount_kurus = self.get_package_amount(package_type)
            amount_tl = amount_kurus / 100
            
            # Sipariş ID oluştur
            order_id = f"LEX_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{package_type[:1].upper()}"
            
            # URL'ler
            current_site = get_current_site(request)
            domain = current_site.domain
            if 'lexatech.ai' not in domain:
                domain = 'lexatech.ai'
            
            success_url = f"https://{domain}/payment/success/"
            fail_url = f"https://{domain}/payment/fail/"
            
            # Hash hesaplama - Param dokümantasyonuna göre
            # Format: CLIENT_CODE + GUID + Taksit + Islem_Tutar + Toplam_Tutar + Siparis_ID + Hata_URL + Basarili_URL
            taksit = "1"
            islem_tutar = f"{amount_tl:.2f}"  # 1000.00 formatında
            toplam_tutar = islem_tutar
            
            hash_string = f"{self.client_code}{self.guid}{taksit}{islem_tutar}{toplam_tutar}{order_id}{fail_url}{success_url}"
            hash_value = self.calculate_hash(hash_string)
            
            # Debug log
            logger.info(f"New Payment Service Debug:")
            logger.info(f"  Hash String: {hash_string}")
            logger.info(f"  Hash Value: {hash_value}")
            
            # Form parametreleri
            form_params = {
                'CLIENT_CODE': self.client_code,
                'CLIENT_USERNAME': self.client_username, 
                'GUID': self.guid,
                'MERCHANT_OID': order_id,
                'TOTAL_AMOUNT': str(amount_kurus),  # Kuruş cinsinden
                'CURRENCY': 'TL',
                'SUCCESS_URL': success_url,
                'FAIL_URL': fail_url,
                'HASH': hash_value,
                'INSTALLMENT_COUNT': '1',
                'TEST_MODE': '0',  # Production
                'PRODUCT_NAME': f'Lexatech {package_type.title()} Abonelik'
            }
            
            logger.info(f"Payment created - Order: {order_id}, Amount: {amount_tl} TL")
            
            return {
                'success': True,
                'payment_url': self.form_url,
                'form_params': form_params,
                'order_id': order_id,
                'amount': amount_tl,
                'requires_redirect': True,
                'is_form': True
            }
            
        except Exception as e:
            logger.error(f"Payment creation error: {str(e)}")
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
