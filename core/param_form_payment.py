# param_form_payment.py - Form-based Payment (SOAP yerine)

import hashlib
import base64
from datetime import datetime
from django.conf import settings
from django.urls import reverse
from django.contrib.sites.shortcuts import get_current_site
import logging

logger = logging.getLogger(__name__)

class ParamFormPayment:
    def __init__(self):
        # Gerçek credentials
        self.client_code = "145942"
        self.guid = "E204D733-02BA-4312-B03F-84BFE184313C"
        self.client_username = "TP10173244"
        self.client_password = "E78A466F0083A439"
        
        # Test modunu settings'den al
        self.test_mode = getattr(settings, 'PARAM_TEST_MODE', True)
        
        # Form URL
        if self.test_mode:
            self.form_url = "https://test-dmz.param.com.tr/tr/param/ParamPayment.aspx"
        else:
            self.form_url = "https://posws.param.com.tr/gateway/payment/form"
        
    def sha2b64(self, data):
        """SHA256 + Base64 hash hesaplama"""
        hash_bytes = hashlib.sha256(data.encode('utf-8')).digest()
        return base64.b64encode(hash_bytes).decode('utf-8')
    
    def get_package_amount(self, package_type):
        """Paket tutarları (kuruş cinsinden)"""
        if self.test_mode:
            amounts = {
                'monthly': 100,       # 1.00 TL
                'quarterly': 250,     # 2.50 TL
                'semi_annual': 450,   # 4.50 TL
                'annual': 1000        # 10.00 TL
            }
        else:
            amounts = {
                'monthly': 100000,      # 1000.00 TL
                'quarterly': 250000,    # 2500.00 TL
                'semi_annual': 450000,  # 4500.00 TL
                'annual': 1000000       # 10000.00 TL
            }
        return amounts.get(package_type, 100 if self.test_mode else 100000)
    
    def create_payment(self, request, package_type):
        """Form-based payment oluştur"""
        try:
            # Tutarlar
            amount_kurus = self.get_package_amount(package_type)
            amount_tl = amount_kurus / 100
            amount_str = f"{amount_tl:.2f}"  # Noktalı format
            
            # Sipariş ID
            order_id = f"{'TEST' if self.test_mode else 'LEX'}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # URL'ler
            current_site = get_current_site(request)
            domain = current_site.domain
            if 'lexatech.ai' not in domain:
                domain = 'lexatech.ai'
            
            success_url = f"https://{domain}/payment/success/"
            fail_url = f"https://{domain}/payment/fail/"
            
            # Hash hesaplama - Form için
            taksit = "1"
            hash_string = f"{self.client_code}{self.guid}{taksit}{amount_str}{amount_str}{order_id}{fail_url}{success_url}"
            hash_value = self.sha2b64(hash_string)
            
            logger.info(f"Form Payment Debug:")
            logger.info(f"  Mode: {'TEST' if self.test_mode else 'PRODUCTION'}")
            logger.info(f"  Amount (kuruş): {amount_kurus}")
            logger.info(f"  Amount (TL): {amount_str}")
            logger.info(f"  Order ID: {order_id}")
            logger.info(f"  Hash String: {hash_string}")
            logger.info(f"  Hash Value: {hash_value}")
            
            # Form parametreleri
            form_params = {
                'CLIENT_CODE': self.client_code,
                'CLIENT_USERNAME': self.client_username,
                'CLIENT_PASSWORD': self.client_password,
                'GUID': self.guid,
                'MODE': 'TEST' if self.test_mode else 'PROD',
                'ORDER_ID': order_id,
                'AMOUNT': str(amount_kurus),
                'INSTALLMENT': taksit,
                'CURRENCY_CODE': '949',  # TL
                'OK_URL': success_url,
                'FAIL_URL': fail_url,
                'HASH': hash_value
            }
            
            # Session'a kaydet
            request.session['payment_info'] = {
                'order_id': order_id,
                'package_type': package_type,
                'amount': amount_tl
            }
            
            return {
                'success': True,
                'payment_url': self.form_url,
                'form_params': form_params,
                'is_form': True,
                'requires_redirect': True
            }
            
        except Exception as e:
            logger.error(f"Form payment error: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f'Form ödeme hatası: {str(e)}'
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
