# core/udf_extractor.py

import logging
import zipfile
import xml.etree.ElementTree as ET
from io import BytesIO

logger = logging.getLogger(__name__)

class UDFExtractor:
    """UYAP UDF dosya formatından metin çıkarma sınıfı"""
    
    def __init__(self):
        self.encodings = [
            'utf-8',
            'windows-1254', 
            'iso-8859-9',
            'cp1252',
            'latin1',
            'ascii'
        ]
    
    def extract_text(self, udf_file):
        """UDF dosyasından metin çıkar"""
        try:
            logger.info(f"UDF metin çıkarma başlıyor: {udf_file.name}")
            
            # Dosya pointer'ını başa al
            udf_file.seek(0)
            file_content = udf_file.read()
            
            if len(file_content) == 0:
                logger.error("UDF dosyası boş")
                return None
            
            logger.info(f"UDF dosya boyutu: {len(file_content)} bytes")
            
            # 1. Önce ZIP olup olmadığını kontrol et (UDF dosyaları genellikle ZIP)
            if self._is_zip_file(file_content):
                logger.info("UDF dosyası ZIP formatında tespit edildi")
                zip_content = self._try_zip_extraction(file_content)
                if zip_content:
                    return zip_content
            
            # 2. ZIP değilse doğrudan metin dosyası olarak okumayı dene
            text_content = self._try_direct_text_decode(file_content)
            if text_content:
                return text_content
            
            # 3. ZIP extraction tekrar dene (ilk deneme başarısızsa)
            if not self._is_zip_file(file_content):
                zip_content = self._try_zip_extraction(file_content)
                if zip_content:
                    return zip_content
            
            # 3. Binary analiz ile metin bulmaya çalış
            binary_content = self._try_binary_analysis(file_content)
            if binary_content:
                return binary_content
            
            # 4. Raw decode (son çare)
            raw_content = self._try_raw_decode(file_content)
            if raw_content:
                return raw_content
            
            logger.error("UDF dosyasından hiçbir yöntemle metin çıkarılamadı")
            return None
            
        except Exception as e:
            logger.error(f"UDF extraction error: {str(e)}", exc_info=True)
            return None
    
    def _is_zip_file(self, file_content):
        """Dosyanın ZIP formatında olup olmadığını kontrol et"""
        # ZIP dosyası magic signatures
        zip_signatures = [
            b'PK\x03\x04',  # Local file header
            b'PK\x05\x06',  # End of central directory
            b'PK\x07\x08',  # Data descriptor
        ]
        
        for signature in zip_signatures:
            if file_content.startswith(signature):
                logger.info(f"ZIP signature tespit edildi: {signature}")
                return True
        
        return False
    
    def _try_direct_text_decode(self, file_content):
        """Doğrudan metin decode etmeyi dene"""
        for encoding in self.encodings:
            try:
                content = file_content.decode(encoding)
                # Anlamlı metin var mı kontrol et
                if len(content.strip()) > 20 and self._is_meaningful_text(content):
                    logger.info(f"UDF doğrudan {encoding} ile decode edildi: {len(content)} karakter")
                    logger.info(f"UDF metin önizleme (ilk 200 karakter): {repr(content[:200])}")
                    
                    # Metni temizle
                    cleaned_content = self._clean_udf_text(content)
                    logger.info(f"UDF metin temizlendi: {len(cleaned_content)} karakter")
                    return cleaned_content
            except UnicodeDecodeError:
                continue
        return None
    
    def _try_zip_extraction(self, file_content):
        """ZIP dosyası olarak açmayı dene"""
        try:
            with zipfile.ZipFile(BytesIO(file_content), 'r') as zip_file:
                logger.info(f"UDF ZIP dosyası açıldı, içerik: {zip_file.namelist()}")
                
                extracted_texts = []
                
                for file_name in zip_file.namelist():
                    logger.info(f"ZIP dosya işleniyor: {file_name}")
                    
                    # Tüm dosyaları işlemeye çalış (uzantı kısıtlaması yok)
                    try:
                        with zip_file.open(file_name) as inner_file:
                            inner_content = inner_file.read()
                            
                            logger.info(f"{file_name} dosya boyutu: {len(inner_content)} bytes")
                            
                            # XML dosyası ise özel işle
                            if file_name.endswith('.xml'):
                                logger.info(f"{file_name} XML olarak işleniyor")
                                xml_text = self._extract_xml_text(inner_content)
                                if xml_text and len(xml_text.strip()) > 20:
                                    logger.info(f"{file_name} XML'den {len(xml_text)} karakter çıkarıldı")
                                    extracted_texts.append(f"=== {file_name} ===\n{xml_text}")
                                else:
                                    logger.warning(f"{file_name} XML'den metin çıkarılamadı")
                            else:
                                # Diğer dosyalar için encoding dene
                                logger.info(f"{file_name} metin dosyası olarak işleniyor")
                                text_extracted = False
                                
                                for encoding in self.encodings:
                                    try:
                                        text = inner_content.decode(encoding)
                                        if len(text.strip()) > 20 and self._is_meaningful_text(text):
                                            logger.info(f"{file_name} {encoding} ile decode edildi: {len(text)} karakter")
                                            extracted_texts.append(f"=== {file_name} ===\n{text.strip()}")
                                            text_extracted = True
                                            break
                                    except UnicodeDecodeError:
                                        continue
                                
                                if not text_extracted:
                                    logger.warning(f"{file_name} dosyasından metin çıkarılamadı")
                                    
                    except Exception as e:
                        logger.error(f"ZIP içindeki dosya okunamadı {file_name}: {str(e)}")
                        continue
                
                if extracted_texts:
                    result = "\n\n".join(extracted_texts)
                    logger.info(f"ZIP'ten {len(extracted_texts)} dosya okundu, toplam: {len(result)} karakter")
                    cleaned_result = self._clean_udf_text(result)
                    logger.info(f"ZIP metin temizlendi: {len(cleaned_result)} karakter")
                    
                    # Debug: temizlenmiş metnin önizlemesi
                    logger.info(f"Temizlenmiş metin önizleme: {repr(cleaned_result[:200])}")
                    return cleaned_result
                else:
                    logger.error("ZIP'ten hiçbir dosyadan metin çıkarılamadı")
                    
        except zipfile.BadZipFile:
            logger.info("UDF dosyası ZIP formatında değil")
        except Exception as e:
            logger.warning(f"ZIP extraction hatası: {str(e)}")
        
        return None
    
    def _extract_xml_text(self, xml_content):
        """XML içeriğinden metin çıkar"""
        try:
            # Farklı encoding'lerle XML parse etmeyi dene
            for encoding in self.encodings:
                try:
                    if isinstance(xml_content, bytes):
                        xml_string = xml_content.decode(encoding)
                    else:
                        xml_string = xml_content
                    
                    root = ET.fromstring(xml_string)
                    text = self._extract_text_from_xml_element(root)
                    if len(text.strip()) > 10:
                        logger.info(f"XML'den {len(text)} karakter metin çıkarıldı")
                        return text.strip()
                except (ET.ParseError, UnicodeDecodeError):
                    continue
            
            # XML parse edilemezse raw text olarak dene
            for encoding in self.encodings:
                try:
                    text = xml_content.decode(encoding) if isinstance(xml_content, bytes) else xml_content
                    if len(text.strip()) > 10:
                        return text.strip()
                except UnicodeDecodeError:
                    continue
                    
        except Exception as e:
            logger.warning(f"XML metin çıkarma hatası: {str(e)}")
        
        return None
    
    def _extract_text_from_xml_element(self, element):
        """XML elementinden tüm metni çıkar"""
        texts = []
        
        if element.text:
            texts.append(element.text.strip())
        
        for child in element:
            child_text = self._extract_text_from_xml_element(child)
            if child_text:
                texts.append(child_text)
            
            if child.tail:
                texts.append(child.tail.strip())
        
        return "\n".join(text for text in texts if text)
    
    def _try_binary_analysis(self, file_content):
        """Binary analiz ile metin bulmaya çalış"""
        # UYAP dosyaları genellikle header'a sahip olabilir
        # Farklı offset'lerden başlayarak okuma dene
        
        for offset in [0, 16, 32, 64, 128, 256, 512, 1024]:
            if offset >= len(file_content):
                continue
                
            chunk = file_content[offset:]
            
            for encoding in self.encodings:
                try:
                    decoded = chunk.decode(encoding, errors='ignore')
                    
                    # Anlamlı metin var mı kontrol et
                    if len(decoded.strip()) > 50 and self._is_meaningful_text(decoded):
                        logger.info(f"Binary analizde offset {offset}, encoding {encoding} ile metin bulundu: {len(decoded)} karakter")
                        cleaned_content = self._clean_udf_text(decoded)
                        logger.info(f"Binary metin temizlendi: {len(cleaned_content)} karakter")
                        return cleaned_content
                except:
                    continue
        
        return None
    
    def _try_raw_decode(self, file_content):
        """Son çare: raw decode"""
        try:
            # Errors='replace' ile decode et
            content = file_content.decode('utf-8', errors='replace')
            if len(content.strip()) > 20:
                logger.info(f"Raw decode ile {len(content)} karakter okundu")
                return content.strip()
        except:
            pass
        
        try:
            # String'e çevir
            content = str(file_content, errors='ignore')
            if len(content.strip()) > 20:
                logger.info(f"String conversion ile {len(content)} karakter okundu")
                return content.strip()
        except:
            pass
        
        return None
    
    def _is_meaningful_text(self, text):
        """Metinin anlamlı olup olmadığını kontrol et"""
        if len(text.strip()) < 10:
            return False
        
        # Alfabetik karakter oranını kontrol et
        alpha_chars = sum(1 for c in text[:500] if c.isalpha())
        total_chars = len(text[:500])
        
        if total_chars == 0:
            return False
        
        alpha_ratio = alpha_chars / total_chars
        
        # En az %20 alfabetik karakter olsun
        return alpha_ratio > 0.2
    
    def _clean_udf_text(self, text):
        """UDF metnini temizle ve düzenle"""
        import re
        
        # Null karakterleri temizle
        text = text.replace('\x00', '')
        
        # Çok fazla boşluk ve control karakterleri temizle
        text = re.sub(r'[\x01-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
        
        # Çoklu boşlukları tek boşluğa çevir
        text = re.sub(r'\s+', ' ', text)
        
        # Çoklu satır sonlarını düzenle
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        # Başlangıç ve sonundaki gereksiz karakterleri temizle
        text = text.strip()
        
        # Eğer metin çok fazla tekrarlanan karakterle başlıyorsa temizle
        # UYAP dosyaları bazen header padding içerebilir
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            # Boş satırları atla
            if not line:
                continue
            
            # Çok fazla tekrarlanan karakterlerden oluşan satırları atla
            if len(set(line)) <= 2 and len(line) > 10:
                continue
                
            # Sadece özel karakterlerden oluşan satırları atla
            if not any(c.isalnum() for c in line):
                continue
                
            cleaned_lines.append(line)
        
        result = '\n'.join(cleaned_lines)
        
        # Minimum anlamlı uzunluk kontrolü
        if len(result.strip()) < 50:
            return text.strip()  # Temizleme çok agresifse orijinali döndür
        
        return result