"""
Param Modal Payment Service - iFrame API (Fixed Format)
"""

import hashlib
import base64
import requests
import json
from datetime import datetime
from django.conf import settings
from django.urls import reverse
from django.contrib.sites.shortcuts import get_current_site
import logging

logger = logging.getLogger(__name__)


class ParamModalService:
    """Param Modal Payment servisi - iFrame API"""
    
    def __init__(self):
        # Test/Production mode
        self.test_mode = getattr(settings, "PARAM_TEST_MODE", False)
        
        if self.test_mode:
            # Test credentials
            self.client_code = "10738"
            self.username = "Test"
            self.password = "Test"
            self.guid = "0C13D406-873B-403B-9C09-A5766840D98C"
            self.soap_url = "https://testposws.param.com.tr/turkpos.ws/service_turkpos_prod.asmx"
        else:
            # Production credentials
            self.client_code = getattr(settings, "PARAM_CLIENT_CODE", "145942")
            self.username = getattr(settings, "PARAM_CLIENT_USERNAME", "TP10173244")
            self.password = getattr(settings, "PARAM_CLIENT_PASSWORD", "E78A466F0083A439")
            self.guid = getattr(settings, "PARAM_GUID", "E204D733-02BA-4312-B03F-84BFE184313C")
            self.soap_url = "https://posws.param.com.tr/turkpos.ws/service_turkpos_prod.asmx"
    
    def get_package_amount(self, package_type):
        """Paket fiyatları (kuruş cinsinden)"""
        prices = {
            "monthly": 100000,      # 1000.00 TL
            "quarterly": 270000,    # 2700.00 TL  
            "semi_annual": 520000,  # 5200.00 TL
            "annual": 1000000,      # 10000.00 TL
        }
        return prices.get(package_type, 100000)
    
    def get_package_description(self, package_type):
        """Paket açıklamaları"""
        descriptions = {
            "monthly": "Lexatech Aylik Abonelik",
            "quarterly": "Lexatech 3 Aylik Abonelik",
            "semi_annual": "Lexatech 6 Aylik Abonelik", 
            "annual": "Lexatech Yillik Abonelik",
        }
        return descriptions.get(package_type, "Lexatech Abonelik")
    
    def create_modal_payment(self, request, package_type):
        """TP_Modal_Payment ile iFrame ödeme sayfası oluştur"""
        try:
            current_site = get_current_site(request)
            
            # Order details
            order_id = f"LEX_{datetime.now().strftime("%Y%m%d_%H%M%S")}_{request.user.id}"
            amount_kurus = self.get_package_amount(package_type)
            amount_tl = amount_kurus / 100
            amount_str = f"{amount_tl:.2f}".replace(".", ",")
            
            # URLs
            domain = current_site.domain
            if domain == "example.com" or "145.223.82.130" in domain:
                domain = "lexatech.ai"
            
            callback_url = f"https://{domain}/payment/success/"
            
            # Transaction ID
            transaction_id = f"TXN_{datetime.now().strftime("%Y%m%d_%H%M%S")}"
            
            # SOAP XML for TP_Modal_Payment (Correct Format)
            soap_body = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
               xmlns:xsd="http://www.w3.org/2001/XMLSchema" 
               xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <TP_Modal_Payment xmlns="https://turkpos.com.tr/">
      <d>
        <Code>{self.client_code}</Code>
        <User>{self.username}</User>
        <Pass>{self.password}</Pass>
        <GUID>{self.guid}</GUID>
        <GSM>5551234567</GSM>
        <Amount>{amount_str}</Amount>
        <Order_ID>{order_id}</Order_ID>
        <TransactionId>{transaction_id}</TransactionId>
        <Callback_URL>{callback_url}</Callback_URL>
        <installment>1</installment>
        <MaxInstallment>12</MaxInstallment>
      </d>
    </TP_Modal_Payment>
  </soap:Body>
</soap:Envelope>"""
            
            # SOAP headers
            headers = {
                "Content-Type": "text/xml; charset=utf-8",
                "SOAPAction": "https://turkpos.com.tr/TP_Modal_Payment",
                "Accept": "text/xml"
            }
            
            logger.info(f"Sending TP_Modal_Payment request - Order: {order_id}, Amount: {amount_tl} TL")
            logger.info(f"SOAP Body: {soap_body}")
            
            response = requests.post(
                self.soap_url,
                data=soap_body.encode("utf-8"),
                headers=headers,
                timeout=30,
                verify=True
            )
            
            if response.status_code == 200:
                return self.parse_modal_response(response, order_id, amount_tl)
            else:
                logger.error(f"Modal payment request failed: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text[:200]}",
                    "order_id": order_id
                }
                
        except Exception as e:
            logger.error(f"Modal payment error: {str(e)}")
            return {
                "success": False,
                "error": f"Modal payment error: {str(e)}",
                "order_id": order_id if "order_id" in locals() else None
            }
    
    def parse_modal_response(self, response, order_id, amount):
        """TP_Modal_Payment response parse et"""
        try:
            logger.info(f"TP_Modal_Payment Response: {response.text}")
            
            # Parse XML response for URL
            import re
            result_code_match = re.search(r"<ResultCode>(\d+)</ResultCode>", response.text)
            result_desc_match = re.search(r"<ResultDescription>(.*?)</ResultDescription>", response.text)
            url_match = re.search(r"<URL>(.*?)</URL>", response.text)
            
            if result_code_match and int(result_code_match.group(1)) > 0:
                if url_match and url_match.group(1):
                    return {
                        "success": True,
                        "payment_url": url_match.group(1),
                        "order_id": order_id,
                        "amount": amount,
                        "requires_redirect": True,
                        "message": "iFrame ödeme sayfası hazır"
                    }
                else:
                    return {
                        "success": False,
                        "error": "iFrame URL bulunamadı",
                        "order_id": order_id
                    }
            else:
                error_msg = result_desc_match.group(1) if result_desc_match else "Bilinmeyen hata"
                return {
                    "success": False,
                    "error": f"Param Error: {error_msg}",
                    "order_id": order_id
                }
                
        except Exception as e:
            logger.error(f"Modal response parse error: {str(e)}")
            return {
                "success": False,
                "error": f"Response parse error: {str(e)}",
                "order_id": order_id
            }
