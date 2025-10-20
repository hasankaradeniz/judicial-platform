import hashlib
import base64

def calculate_param_hash(client_code, guid, taksit, amount_str, order_id, fail_url, success_url):
    """
    Param TP_WMD_UCD için doğru hash hesaplama
    Format: CLIENT_CODE + GUID + Taksit + Islem_Tutar + Toplam_Tutar + Siparis_ID + Hata_URL + Basarili_URL
    """
    hash_string = f"{client_code}{guid}{taksit}{amount_str}{amount_str}{order_id}{fail_url}{success_url}"
    
    # SHA256 + Base64 - URL encoding YOK
    hash_bytes = hashlib.sha256(hash_string.encode("utf-8")).digest()
    hash_value = base64.b64encode(hash_bytes).decode("utf-8")
    
    print(f"Hash String: {hash_string}")
    print(f"Hash Value: {hash_value}")
    
    return hash_value

if __name__ == "__main__":
    # Test hash calculation
    test_hash = calculate_param_hash(
        "145942",
        "E204D733-02BA-4312-B03F-84BFE184313C", 
        "1",
        "100,00",
        "TEST_ORDER_123",
        "https://lexatech.ai/payment-fail",
        "https://lexatech.ai/payment-success"
    )
    print(f"Test Hash: {test_hash}")
