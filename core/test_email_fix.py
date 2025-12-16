import re

# Dosyayı oku
with open("core/daily_gazette_service.py", "r") as f:
    content = f.read()

# Test metodunu tamamen değiştir
new_test_method = """    def test_email_system(self, user_email):
        \"\"\"
        Email sistemini test et
        \"\"\"
        try:
            logger.info(f"Email sistemi test ediliyor: {user_email}")
            
            # Test icerigi olustur - Model instance simulation
            class TestGazetteContent:
                def __init__(self, title, category, link, summary):
                    self.title = title
                    self.category = category
                    self.original_url = link
                    self.summary = summary
                
                def get_category_display(self):
                    return self.category
            
            test_content = [
                TestGazetteContent(
                    title="Test - Yonetmelik Ornegi",
                    category="Yonetmelik", 
                    link="https://resmigazete.gov.tr/test",
                    summary="Bu bir test yonetmeligi ozetidir."
                )
            ]
            
            # Test kullanicisi
            class TestUser:
                def __init__(self, email):
                    self.email = email
                    self.username = "test_user"
                    self.first_name = "Test"
                    self.id = 999999
            
            user = TestUser(user_email)
            
            # HTML olustur
            html_content = self._generate_email_html(user, test_content, date.today())
            
            # Email gonder
            send_mail(
                subject="LexaTech - Test Email",
                message="Bu bir test emailidir.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user_email],
                html_message=html_content,
                fail_silently=False,
            )
            
            logger.info(f"Test email basariyla gonderildi: {user_email}")
            return True
            
        except Exception as e:
            logger.error(f"Test email hatasi: {str(e)}")
            return False"""

# Eski test metodunu bul ve değiştir
pattern = r"def test_email_system\(self, user_email\):.*?(?=    def|\Z)"
content = re.sub(pattern, new_test_method, content, flags=re.DOTALL)

# Dosyayı yaz
with open("core/daily_gazette_service.py", "w") as f:
    f.write(content)

print("Test metodu düzeltildi")
