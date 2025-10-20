# core/admin_pdf_processor.py

import os
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from io import BytesIO
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from core.models import (
    MevzuatGelismis, MevzuatTuru, MevzuatKategori,
    MevzuatMadde, MevzuatDegisiklik, MevzuatLog
)

try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

class PDFProcessor:
    """Admin için PDF ve UDF işleme sınıfı"""
    
    def __init__(self):
        self.stats = {
            'processed': 0,
            'saved': 0,
            'errors': 0,
            'messages': []
        }
    
    def process_file(self, file_obj, mevzuat_type='kanun', admin_user=None):
        """Tek bir dosyayı işle (PDF veya UDF)"""
        try:
            file_name = file_obj.name.lower()
            
            # Dosya türüne göre metin çıkar
            if file_name.endswith('.pdf'):
                if not PDF_AVAILABLE:
                    raise Exception("PyPDF2 paketi kurulu değil. Lütfen 'pip install PyPDF2' komutunu çalıştırın.")
                text_content = self.extract_text_from_pdf(file_obj)
            elif file_name.endswith('.udf'):
                text_content = self.extract_text_from_udf(file_obj)
            else:
                raise Exception(f"Desteklenmeyen dosya türü: {file_name}")
            
            if not text_content or len(text_content) < 100:
                raise Exception("Dosyadan yeterli metin çıkarılamadı")
            
            # Mevzuat verilerini parse et
            mevzuat_data = self.parse_content(text_content, file_obj.name, mevzuat_type)
            
            # Veritabanına kaydet
            mevzuat = self.save_to_database(mevzuat_data, file_obj, admin_user)
            
            self.stats['processed'] += 1
            self.stats['saved'] += 1
            self.stats['messages'].append(f"✅ {mevzuat.baslik} başarıyla kaydedildi")
            
            return mevzuat
            
        except Exception as e:
            self.stats['errors'] += 1
            self.stats['messages'].append(f"❌ {pdf_file.name}: {str(e)}")
            raise
    
    def extract_text_from_pdf(self, pdf_file):
        """PDF'den metin çıkar"""
        try:
            text = ""
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            
            return text.strip()
            
        except Exception as e:
            raise Exception(f"PDF metin çıkarma hatası: {str(e)}")
    
    def extract_text_from_udf(self, udf_file):
        """UDF (UYAP Döküman Formatı) dosyasından metin çıkar"""
        try:
            file_content = udf_file.read()
            
            # Önce doğrudan metin olarak okumayı dene
            for encoding in ['utf-8', 'windows-1254', 'iso-8859-9']:
                try:
                    content = file_content.decode(encoding)
                    return content.strip()
                except UnicodeDecodeError:
                    continue
            
            # ZIP dosyası olarak açmayı dene
            try:
                with zipfile.ZipFile(BytesIO(file_content), 'r') as zip_file:
                    extracted_content = []
                    
                    for file_name in zip_file.namelist():
                        if file_name.endswith(('.xml', '.txt', '.rtf')):
                            with zip_file.open(file_name) as inner_file:
                                inner_content = inner_file.read()
                                
                                # Farklı encoding'leri dene
                                for encoding in ['utf-8', 'windows-1254', 'iso-8859-9']:
                                    try:
                                        text = inner_content.decode(encoding)
                                        extracted_content.append(text)
                                        break
                                    except UnicodeDecodeError:
                                        continue
                        
                        elif file_name.endswith('.xml'):
                            # XML dosyalarından metin çıkar
                            try:
                                with zip_file.open(file_name) as inner_file:
                                    xml_content = inner_file.read()
                                    
                                    try:
                                        root = ET.fromstring(xml_content)
                                        xml_text = self._extract_text_from_xml(root)
                                        if xml_text:
                                            extracted_content.append(xml_text)
                                    except ET.ParseError:
                                        # XML parsing başarısız, ham metin olarak dene
                                        for encoding in ['utf-8', 'windows-1254', 'iso-8859-9']:
                                            try:
                                                text = xml_content.decode(encoding)
                                                extracted_content.append(text)
                                                break
                                            except UnicodeDecodeError:
                                                continue
                            except Exception:
                                continue
                    
                    if extracted_content:
                        return "\n\n".join(extracted_content)
                        
            except zipfile.BadZipFile:
                pass
            
            # Son çare: raw bytes'ı string'e çevir
            try:
                content = str(file_content, errors='ignore')
                return content.strip()
            except Exception:
                pass
            
            raise Exception("UDF dosyası hiçbir yöntemle okunamadı")
            
        except Exception as e:
            raise Exception(f"UDF metin çıkarma hatası: {str(e)}")
    
    def _extract_text_from_xml(self, element):
        """XML elementinden tüm metin içeriğini çıkar"""
        text_content = []
        
        if element.text:
            text_content.append(element.text.strip())
        
        for child in element:
            child_text = self._extract_text_from_xml(child)
            if child_text:
                text_content.append(child_text)
            
            if child.tail:
                text_content.append(child.tail.strip())
        
        return "\n".join(text_content).strip()
    
    def parse_content(self, text, filename, mevzuat_type):
        """PDF içeriğini parse et"""
        try:
            data = {
                'baslik': '',
                'mevzuat_numarasi': '',
                'yayin_tarihi': None,
                'resmi_gazete_tarihi': None,
                'resmi_gazete_sayisi': '',
                'tam_metin': text,
                'mevzuat_turu': mevzuat_type,
                'kategori': mevzuat_type,
                'kaynak': 'admin_upload'
            }
            
            # Dosya adından mevzuat numarası çıkar
            filename_clean = Path(filename).stem
            number_match = re.search(r'\b(\d{4,5})\b', filename_clean)
            if number_match:
                data['mevzuat_numarasi'] = number_match.group(1)
            
            # Metinden başlık çıkar
            lines = text.split('\n')
            for i, line in enumerate(lines[:15]):
                line = line.strip()
                if (len(line) > 15 and len(line) < 200 and 
                    ('KANUN' in line.upper() or 'YÖNETMELIK' in line.upper() or 
                     'KARARNAME' in line.upper() or 'TÜZÜK' in line.upper()) and
                    not any(skip in line for skip in ['Madde', 'madde', 'Kanun Numarası', ':', 'Kabul Tarihi', 'RG'])):
                    
                    # Çok satırlı başlık kontrolü
                    if len(line) < 100 and i < len(lines) - 1:
                        next_line = lines[i + 1].strip()
                        if (len(next_line) > 10 and len(next_line) < 100 and 
                            not any(skip in next_line for skip in ['Madde', 'RG', 'Sayı', 'Tarih'])):
                            combined_title = f"{line} {next_line}".strip()
                            if len(combined_title) < 200:
                                data['baslik'] = combined_title
                                break
                    
                    data['baslik'] = line
                    break
            
            # Eğer başlık bulunamadıysa dosya adından oluştur
            if not data['baslik']:
                clean_filename = re.sub(r'[^\w\s-]', '', filename_clean)
                clean_filename = re.sub(r'[-\s]+', ' ', clean_filename)
                data['baslik'] = clean_filename.title()
            
            # Resmi Gazete bilgilerini çıkar
            rg_patterns = [
                r'Resmî?\s*Gazete.*?(\d{1,2}[./]\d{1,2}[./]\d{4})',
                r'RG.*?(\d{1,2}[./]\d{1,2}[./]\d{4})',
                r'Sayı\s*:\s*(\d+).*?Tarih\s*:\s*(\d{1,2}[./]\d{1,2}[./]\d{4})'
            ]
            
            for pattern in rg_patterns:
                try:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        if len(match.groups()) == 2:  # Sayı ve tarih
                            data['resmi_gazete_sayisi'] = match.group(1)
                            data['resmi_gazete_tarihi'] = match.group(2)
                        else:  # Sadece tarih
                            data['resmi_gazete_tarihi'] = match.group(1)
                        break
                except Exception:
                    continue
            
            # Kanun numarası ve tarih çıkar
            kanun_patterns = [
                r'Kanun\s*No\s*:\s*(\d+)',
                r'(\d+)\s*sayılı',
                r'Kabul\s*Tarihi\s*:\s*(\d{1,2}[./]\d{1,2}[./]\d{4})'
            ]
            
            for pattern in kanun_patterns:
                try:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        if 'Kabul' in pattern:
                            data['yayin_tarihi'] = match.group(1)
                        else:
                            data['mevzuat_numarasi'] = match.group(1)
                except Exception:
                    continue
            
            return data
            
        except Exception as e:
            raise Exception(f"PDF parse hatası: {str(e)}")
    
    def save_to_database(self, data, pdf_file, admin_user):
        """Veritabanına kaydet"""
        try:
            with transaction.atomic():
                # Mevzuat türü
                mevzuat_turu, created = MevzuatTuru.objects.get_or_create(
                    kod=data['mevzuat_turu'],
                    defaults={
                        'ad': data['mevzuat_turu'].title(),
                        'kategori': data['mevzuat_turu'],
                        'sira': 1,
                        'aktif': True
                    }
                )
                
                # Kategori
                kategori, created = MevzuatKategori.objects.get_or_create(
                    kod=data['kategori'],
                    defaults={
                        'ad': data['kategori'].title(),
                        'aciklama': f'Admin upload - {data["kategori"]}',
                        'aktif': True
                    }
                )
                
                # Unique ID oluştur
                if data['mevzuat_numarasi']:
                    mevzuat_id = f"admin_{data['mevzuat_turu']}_{data['mevzuat_numarasi']}"
                else:
                    # Başlıktan hash oluştur
                    baslik_hash = abs(hash(data['baslik'][:50]))
                    mevzuat_id = f"admin_{data['mevzuat_turu']}_{baslik_hash}"
                
                # Dosyayı kaydet
                pdf_path = None
                if pdf_file:
                    pdf_path = default_storage.save(
                        f"mevzuat_pdfs/{mevzuat_id}.pdf",
                        ContentFile(pdf_file.read())
                    )
                
                # Tarihleri Django formatına çevir
                yayin_tarihi = None
                if data.get('yayin_tarihi'):
                    yayin_tarihi = self._convert_date_format(data['yayin_tarihi'])
                
                resmi_gazete_tarihi = None
                if data.get('resmi_gazete_tarihi'):
                    resmi_gazete_tarihi = self._convert_date_format(data['resmi_gazete_tarihi'])
                
                # Mevzuat kaydı
                mevzuat, created = MevzuatGelismis.objects.update_or_create(
                    mevzuat_gov_tr_id=mevzuat_id,
                    defaults={
                        'baslik': data['baslik'] or 'Admin Upload',
                        'mevzuat_turu': mevzuat_turu,
                        'kategori': kategori,
                        'mevzuat_numarasi': data['mevzuat_numarasi'],
                        'yayin_tarihi': yayin_tarihi,
                        'resmi_gazete_tarihi': resmi_gazete_tarihi,
                        'resmi_gazete_sayisi': data.get('resmi_gazete_sayisi', ''),
                        'tam_metin': data['tam_metin'],
                        'kaynak_url': pdf_path or '',
                        'durum': 'yurutulme'
                    }
                )
                
                # Log kaydı
                if admin_user:
                    MevzuatLog.objects.create(
                        mevzuat=mevzuat,
                        islem_turu='admin_upload',
                        aciklama=f'PDF upload: {pdf_file.name}',
                        kullanici_id=admin_user.id if hasattr(admin_user, 'id') else None
                    )
                
                return mevzuat
                
        except Exception as e:
            raise Exception(f"Veritabanı kayıt hatası: {str(e)}")
    
    def _convert_date_format(self, date_str):
        """Tarih formatını DD/MM/YYYY'den YYYY-MM-DD'ye çevir"""
        if not date_str:
            return None
        
        try:
            # DD/MM/YYYY formatından parse et
            if '/' in date_str:
                parts = date_str.split('/')
                if len(parts) == 3:
                    day, month, year = parts
                    return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
            elif '.' in date_str:
                parts = date_str.split('.')
                if len(parts) == 3:
                    day, month, year = parts
                    return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
            
            return None
        except Exception:
            return None
    
    def get_stats(self):
        """İşlem istatistiklerini döndür"""
        return self.stats