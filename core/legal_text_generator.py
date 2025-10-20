import re
# core/legal_text_generator.py

import logging
import os
import zipfile
import xml.etree.ElementTree as ET
from django.core.cache import cache
from datetime import datetime, timedelta
import re
import PyPDF2
from docx import Document
from io import BytesIO
import google.generativeai as genai
from django.conf import settings

logger = logging.getLogger(__name__)

class LegalTextGenerator:

    def clean_asterisks(self, text):
        """Metinden yıldız işaretlerini temizle"""
        if not text:
            return text
        
        # Çift yıldızları temizle (bold **text**)
        text = re.sub(r"\*\*([^*]+?)\*\*", r"\1", text)
        
        # Tek yıldızları temizle (italic *text*)
        text = re.sub(r"\*([^*]+?)\*", r"\1", text)
        
        # Başta ve sonda kalan yıldızları temizle
        text = re.sub(r"^\*+|\*+$", "", text, flags=re.MULTILINE)
        
        # Ardışık yıldızları temizle
        text = re.sub(r"\*{2,}", "", text)
        
        return text.strip()


    """Hukuki Metin Üretici - Dilekçe, sözleşme ve görüş taslakları oluşturur"""
    
    def __init__(self):
        # Gemini API'yi yapılandır
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.gemini_model = genai.GenerativeModel(model_name="gemini-2.5-pro")
        
        self.templates = {
            'dilekce': {
                'name': 'Dava Dilekçesi',
                'description': 'Çeşitli dava türleri için dilekçe taslağı',
                'subtypes': ['alacak', 'boşanma', 'iş', 'miras', 'tapu'],
                'required_fields': ['mahkeme', 'davaci', 'davali', 'konu', 'talep']
            },
            'sozlesme': {
                'name': 'Sözleşme',
                'description': 'Çeşitli türlerde sözleşme taslağı',
                'subtypes': ['satış', 'kira', 'iş', 'ortaklık', 'hizmet'],
                'required_fields': ['taraf1', 'taraf2', 'konu', 'bedel', 'süre']
            },
            'gorus': {
                'name': 'Hukuki Görüş',
                'description': 'Hukuki meselelere ilişkin görüş taslağı',
                'subtypes': ['mütalaa', 'rapor', 'inceleme'],
                'required_fields': ['konu', 'mevzuat', 'sonuc']
            },
            'cevap': {
                'name': 'Cevap Dilekçesi',
                'description': 'Dava cevap dilekçesi taslağı',
                'subtypes': ['red', 'kabul', 'kısmi'],
                'required_fields': ['mahkeme', 'dava_no', 'savunma']
            },
            'temyiz': {
                'name': 'Temyiz Dilekçesi',
                'description': 'Temyiz başvuru dilekçesi',
                'subtypes': ['hukuk', 'ceza'],
                'required_fields': ['mahkeme', 'karar_tarihi', 'temyiz_nedeni']
            }
        }

    def get_available_templates(self):
        """Mevcut şablonları listele"""
        return self.templates

    def generate_from_multiple_documents(self, uploaded_files, document_type, additional_instructions=None):
        """Çoklu belgeye istinaden metin üret"""
        try:
            logger.info(f"Çoklu belge üretimi başlatılıyor - Dosya sayısı: {len(uploaded_files)}, Tür: {document_type}")
            
            # Tüm dosyaların içeriğini çıkar
            all_content = []
            file_summaries = []
            
            for i, uploaded_file in enumerate(uploaded_files):
                logger.info(f"Dosya {i+1}/{len(uploaded_files)} işleniyor: {uploaded_file.name}")
                
                document_content = self._extract_document_content(uploaded_file)
                
                if document_content:
                    all_content.append(f"=== BELGE {i+1}: {uploaded_file.name} ===\n{document_content}\n")
                    file_summaries.append({
                        'name': uploaded_file.name,
                        'length': len(document_content),
                        'type': os.path.splitext(uploaded_file.name)[1].lower(),
                    'is_udf': uploaded_file.name.lower().endswith('.udf')
                    })
                else:
                    logger.warning(f"Dosya içeriği çıkarılamadı: {uploaded_file.name}")
            
            if not all_content:
                return {
                    'success': False,
                    'error': 'Hiçbir belgeden içerik çıkarılamadı'
                }
            
            # Tüm içerikleri birleştir
            combined_content = "\n\n".join(all_content)
            logger.info(f"Birleştirilmiş içerik uzunluğu: {len(combined_content)} karakter")
            
            # AI ile belge analizi ve metin üretimi
            logger.info("AI tabanlı çoklu belge üretimi başlatılıyor...")
            generated_text = self._generate_multi_document_based_text(
                combined_content, document_type, additional_instructions, file_summaries
            )
            
            logger.info(f"AI üretim durumu: {'Başarılı' if generated_text else 'Başarısız'}")
            if generated_text:
                logger.info(f"Üretilen metin uzunluğu: {len(generated_text)} karakter")
            
            return {
                'success': True,
                'document': {
                    'content': self.clean_asterisks(generated_text),
                    'source_documents': [f.name for f in uploaded_files],
                    'document_type': document_type,
                    'generation_date': datetime.now().isoformat(),
                    'word_count': len(generated_text.split()) if generated_text else 0,
                    'template_name': f"{document_type}",
                    'file_count': len(uploaded_files),
                    'additional_instructions': additional_instructions
                }
            }
            
        except Exception as e:
            logger.error(f"Multiple document generation error: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f'Çoklu belge üretimi sırasında hata oluştu: {str(e)}'
            }

    def generate_from_uploaded_document(self, uploaded_file, document_type, additional_params=None):
        """Yüklenen belgeye istinaden metin üret"""
        try:
            logger.info(f"Belge üretimi başlatılıyor - Dosya: {uploaded_file.name}, Tür: {document_type}")
            
            # Dosya içeriğini çıkar
            document_content = self._extract_document_content(uploaded_file)
            
            logger.info(f"İçerik çıkarma durumu: {'Başarılı' if document_content else 'Başarısız'}")
            if document_content:
                logger.info(f"Çıkarılan içerik uzunluğu: {len(document_content)} karakter")
            
            if not document_content:
                return {
                    'success': False,
                    'error': 'Belge içeriği çıkarılamadı'
                }
            
            # AI ile belge analizi ve metin üretimi
            logger.info("AI tabanlı belge üretimi başlatılıyor...")
            generated_text = self._generate_ai_based_document(
                document_content, document_type, additional_params
            )
            
            logger.info(f"AI üretim durumu: {'Başarılı' if generated_text else 'Başarısız'}")
            if generated_text:
                logger.info(f"Üretilen metin uzunluğu: {len(generated_text)} karakter")
            
            return {
                'success': True,
                'document': {
                    'content': self.clean_asterisks(generated_text),
                    'source_document': uploaded_file.name,
                    'document_type': document_type,
                    'generation_date': datetime.now().isoformat(),
                    'word_count': len(generated_text.split()) if generated_text else 0,
                    'template_name': f"{document_type.replace('_', ' ').title()}"
                }
            }
            
        except Exception as e:
            logger.error(f"Document-based generation error: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f'Belge tabanlı üretim sırasında hata oluştu: {str(e)}'
            }

    def _extract_document_content(self, uploaded_file):
        """Yüklenen dosyadan içerik çıkar"""
        try:
            file_name = uploaded_file.name.lower()
            logger.info(f"Dosya içeriği çıkarılıyor: {file_name}")
            
            if file_name.endswith('.pdf'):
                content = self._extract_pdf_content(uploaded_file)
            elif file_name.endswith('.docx'):
                content = self._extract_docx_content(uploaded_file)
            elif file_name.endswith('.txt'):
                content = uploaded_file.read().decode('utf-8')
            elif file_name.endswith('.udf'):
                content = self._extract_udf_content(uploaded_file)
            else:
                logger.error(f"Desteklenmeyen dosya türü: {file_name}")
                return None
            
            logger.info(f"İçerik çıkarma başarılı, uzunluk: {len(content) if content else 0}")
            return content
                
        except Exception as e:
            logger.error(f"Content extraction error: {str(e)}", exc_info=True)
            return None

    def _extract_pdf_content(self, pdf_file):
        """PDF içeriğini çıkar"""
        try:
            logger.info("PDF içeriği çıkarılıyor...")
            pdf_reader = PyPDF2.PdfReader(BytesIO(pdf_file.read()))
            text = ""
            
            logger.info(f"PDF sayfa sayısı: {len(pdf_reader.pages)}")
            
            for i, page in enumerate(pdf_reader.pages):
                page_text = page.extract_text()
                text += page_text + "\n"
                logger.info(f"Sayfa {i+1} işlendi, metin uzunluğu: {len(page_text)}")
            
            result = text.strip()
            logger.info(f"PDF çıkarma tamamlandı, toplam uzunluk: {len(result)}")
            return result
            
        except Exception as e:
            logger.error(f"PDF extraction error: {str(e)}", exc_info=True)
            return None

    def _extract_docx_content(self, docx_file):
        """DOCX içeriğini çıkar"""
        try:
            doc = Document(BytesIO(docx_file.read()))
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            return text.strip()
            
        except Exception as e:
            logger.error(f"DOCX extraction error: {str(e)}")
            return None
    
    def _extract_udf_content(self, udf_file):
        """UDF (UYAP Döküman Formatı) içeriğini çıkar"""
        try:
            logger.info(f"UDF dosyası içeriği çıkarılıyor: {udf_file.name}")
            
            # UDF Extractor kullan
            from .udf_extractor import UDFExtractor
            extractor = UDFExtractor()
            
            content = extractor.extract_text(udf_file)
            
            if content and len(content.strip()) > 10:
                logger.info(f"UDF dosyasından başarıyla metin çıkarıldı: {len(content)} karakter")
                return content
            else:
                logger.error("UDF dosyasından metin çıkarılamadı")
                return None
                
        except Exception as e:
            logger.error(f"UDF extraction error: {str(e)}", exc_info=True)
            return None
    
    def _extract_text_from_xml(self, element):
        """XML elementinden tüm metin içeriğini çıkar"""
        text_content = []
        
        # Element'in kendi text içeriği
        if element.text:
            text_content.append(element.text.strip())
        
        # Alt elementlerin text içeriği
        for child in element:
            child_text = self._extract_text_from_xml(child)
            if child_text:
                text_content.append(child_text)
            
            # Element'in tail text'i
            if child.tail:
                text_content.append(child.tail.strip())
        
        return "\n".join(text_content).strip()

    def _generate_ai_based_document(self, source_content, document_type, additional_params=None):
        """AI ile belge tabanlı metin üretimi"""
        try:
            logger.info(f"AI belge üretimi başlıyor - Tür: {document_type}")
            
            # Eğer Gemini çalışmıyorsa direkt fallback kullan
            if not hasattr(self, 'gemini_model') or self.gemini_model is None:
                logger.warning("Gemini model bulunamadı, fallback kullanılıyor")
                return self._generate_fallback_document(document_type, additional_params)
            
            # Kaynak belgeyi analiz et
            analysis_prompt = f"""
            Aşağıdaki hukuki belgeyi analiz et ve önemli bilgileri çıkar:
            
            BELGE İÇERİĞİ:
            {source_content[:3000]}  # İlk 3000 karakter
            
            Şu bilgileri çıkar:
            1. Belge türü (dilekçe, sözleşme, karar, vb.)
            2. Taraflar (davacı, davalı, taraf1, taraf2, vb.)
            3. Dava konusu/sözleşme konusu
            4. Önemli tarihler
            5. Para miktarları
            6. Hukuki gerekçeler
            7. Mahkeme bilgileri (varsa)
            
            Analiz sonucunu JSON formatında ver:
            """
            
            logger.info("Gemini analiz başlatılıyor...")
            try:
                analysis_response = self.gemini_model.generate_content(analysis_prompt)
                logger.info(f"Analiz tamamlandı, uzunluk: {len(analysis_response.text) if analysis_response.text else 0}")
            except Exception as e:
                logger.error(f"Gemini analiz hatası: {str(e)}")
                return self._generate_fallback_document(document_type, additional_params)
            
            # Üretilecek belge türüne göre prompt hazırla
            generation_prompt = self._build_generation_prompt(
                source_content, document_type, analysis_response.text, additional_params
            )
            
            logger.info("Gemini belge üretimi başlatılıyor...")
            try:
                # Belgeyi üret
                generation_response = self.gemini_model.generate_content(generation_prompt)
                
                if generation_response.text and len(generation_response.text.strip()) > 50:
                    logger.info(f"Belge üretimi başarılı, uzunluk: {len(generation_response.text)}")
                    generated_text = self.clean_markdown_formatting(generation_response.text)
                    return generated_text
                else:
                    logger.warning("Gemini boş/yetersiz yanıt verdi, fallback kullanılıyor")
                    return self._generate_fallback_document(document_type, additional_params)
                    
            except Exception as e:
                logger.error(f"Gemini üretim hatası: {str(e)}")
                return self._generate_fallback_document(document_type, additional_params)
            
        except Exception as e:
            logger.error(f"AI-based generation error: {str(e)}", exc_info=True)
            return self._generate_fallback_document(document_type, additional_params)

    def _build_generation_prompt(self, source_content, document_type, analysis, additional_params=None):
        """Belge üretimi için prompt oluştur"""
        
        base_prompt = f"""
        Sen bir hukuk uzmanısın. Aşağıdaki kaynak belgeye istinaden {document_type} hazırlayacaksın.
        
        KAYNAK BELGE ANALİZİ:
        {analysis}
        
        KAYNAK BELGE İÇERİĞİ:
        {source_content[:2000]}
        
        """
        
        if document_type == 'cevap_dilekçesi':
            prompt = base_prompt + f"""
            Yukarıdaki dava dilekçesine karşı profesyonel bir CEVAP DİLEKÇESİ hazırla.
            
            Cevap dilekçesi şu unsurları içermeli:
            1. Uygun mahkeme başlığı
            2. Dava numarası (kaynak belgeden)
            3. Davacının iddialarına karşı savunma
            4. Hukuki gerekçeler
            5. Delil listesi
            6. Sonuç ve talep
            
            Savunma stratejisi:
            - Davacının iddialarını tek tek ele al
            - Her iddiaya karşı hukuki ve fiili savunma yap
            - İlgili mevzuata atıf yap
            - Profesyonel ve saygılı dil kullan
            
            Türk hukuk sistemine uygun format kullan. ASLA asterisk (*) veya markdown formatlaması kullanma. Vurgu için BÜYÜK HARF kullan.
            """
            
        elif document_type == 'karşı_dava':
            prompt = base_prompt + f"""
            Yukarıdaki dava dilekçesine karşı KARŞI DAVA DİLEKÇESİ hazırla.
            
            Karşı dava şu unsurları içermeli:
            1. Aynı mahkeme başlığı
            2. Karşı dava konusu
            3. Karşı davanın gerekçeleri
            4. Talep edilen hususlar
            5. Delil listesi
            
            Türk hukuk sistemine uygun format kullan. ASLA asterisk (*) veya markdown formatlaması kullanma. Vurgu için BÜYÜK HARF kullan.
            """
            
        elif document_type == 'temyiz_dilekçesi':
            prompt = base_prompt + f"""
            Yukarıdaki mahkeme kararına karşı TEMYİZ DİLEKÇESİ hazırla.
            
            Temyiz dilekçesi şu unsurları içermeli:
            1. Yargıtay daire başlığı
            2. Karar bilgileri
            3. Temyiz nedenleri
            4. Hukuki gerekçeler
            5. Bozma talebi
            
            Türk hukuk sistemine uygun format kullan. ASLA asterisk (*) veya markdown formatlaması kullanma. Vurgu için BÜYÜK HARF kullan.
            """
            
        elif document_type == 'icra_takip':
            prompt = base_prompt + f"""
            Yukarıdaki belgeye istinaden İCRA TAKİP BAŞVURUSU hazırla.
            
            İcra takip başvurusu şu unsurları içermeli:
            1. İcra müdürlüğü başlığı
            2. Alacaklı ve borçlu bilgileri
            3. Alacak miktarı ve dayanağı
            4. Takip talebi
            
            Türk hukuk sistemine uygun format kullan. ASLA asterisk (*) veya markdown formatlaması kullanma. Vurgu için BÜYÜK HARF kullan.
            """
            
        else:
            prompt = base_prompt + f"""
            Yukarıdaki belgeye istinaden {document_type} hazırla.
            Türk hukuk sistemine uygun format ve terminoloji kullan.
            Profesyonel ve hukuki standartlara uygun. Asterisk (*) kullanma, vurgu için BÜYÜK HARF kullan metin üret.
            """
        
        if additional_params:
            prompt += f"\n\nEK PARAMETRELER: {additional_params}"
            
        return prompt

    def _generate_fallback_document(self, document_type, additional_params=None):
        """AI başarısız olduğunda fallback belge"""
        
        logger.info(f"Fallback belge üretiliyor - Tür: {document_type}")
        
        fallback_templates = {
            'cevap_dilekçesi': f"""CEVAP DİLEKÇESİ

SAYIN MAHKEME BAŞKANLIĞINA

DAVA NO: [DAVA NUMARASI]

DAVALININ CEVABI

SAYGILI MAHKEME BAŞKANLIĞI,

Davacının dava dilekçesinde ileri sürdüğü iddialara karşı aşağıdaki cevaplarımı sunarım:

1. MADDI OLAYLAR HAKKINDA:
Davacının dava dilekçesinde yer alan iddialar gerçeği yansıtmamaktadır. [DETAYLAR BELIRTILECEK]

2. HUKUKİ DEĞERLENDİRME:
[HUKUKİ SAVUNMA İÇERİĞİ BURAYA YAZILACAK]

3. SONUÇ:
Yukarıda açıklanan nedenlerle davanın tümüyle reddine karar verilmesini saygılarımla arz ve talep ederim.

{datetime.now().strftime('%d/%m/%Y')}

                                                    DAVALI VEKİLİ
                                        [VEKİL ADI]
""",
            
            'karşı_dava': f"""KARŞI DAVA DİLEKÇESİ

SAYIN MAHKEME BAŞKANLIĞINA

KARŞI DAVACI: [KARŞI DAVACI ADI]
KARŞI DAVALI: [KARŞI DAVALI ADI]

KARŞI DAVA KONUSU: [KONU]

SAYGILI MAHKEME BAŞKANLIĞI,

Ana davaya istinaden açmış olduğum karşı dava hakkında aşağıdaki hususları arz ederim:

[KARŞI DAVA GEREKÇELERİ]

Bu nedenlerle talebimin kabulüne karar verilmesini saygılarımla arz ederim.

{datetime.now().strftime('%d/%m/%Y')}

                                                    KARŞI DAVACI VEKİLİ
                                        [VEKİL ADI]
""",
            
            'temyiz_dilekçesi': f"""TEMYİZ DİLEKÇESİ

YARGITAY [DAİRE] HUKUK DAİRESİ BAŞKANLIĞINA

KARAR VEREN MAHKEME: [MAHKEME ADI]
KARAR TARİHİ: [KARAR TARİHİ]
KARAR NO: [KARAR NUMARASI]

TEMYİZ EDEN: [TEMYİZ EDEN ADI]

SAYGILI YARGITAY BAŞKANLIĞI,

Yukarıda tarih ve numarası yazılı mahkeme kararına karşı aşağıdaki gerekçelerle temyiz başvurusunda bulunuyorum:

TEMYİZ NEDENLERİ:

1. [TEMYİZ NEDENİ 1]
2. [TEMYİZ NEDENİ 2]
3. [TEMYİZ NEDENİ 3]

SONUÇ:
Yukarıda açıklanan nedenlerle kararın bozulmasına karar verilmesini saygılarımla arz ederim.

{datetime.now().strftime('%d/%m/%Y')}

                                                    VEKİL
                                        [VEKİL ADI]
""",

            'icra_takip': f"""İCRA TAKİP BAŞVURUSU

SAYIN İCRA MÜDÜRLÜĞÜNE

ALACAKLI: [ALACAKLI ADI]
BORÇLU: [BORÇLU ADI]

ALACAK MİKTARI: [TUTAR] TL
ALACAK KONUSU: [KONU]

SAYGILI İCRA MÜDÜRLÜĞÜ,

Yukarıda kimlik bilgileri yazılı borçlu aleyhine aşağıdaki alacağım için icra takibi başlatılmasını talep ederim:

ALACAK DAYANAĞI:
[ALACAK DAYANAĞI]

ALACAK MİKTARI: [TUTAR] TL

Gereğini saygılarımla arz ederim.

{datetime.now().strftime('%d/%m/%Y')}

                                                    ALACAKLI
                                        [ALACAKLI ADI]
"""
        }
        
        result = fallback_templates.get(document_type, f"""
{document_type.replace('_', ' ').upper()} BELGESI

[BELGE İÇERİĞİ BURAYA YAZILACAKTIR]

{datetime.now().strftime('%d/%m/%Y')}

[İMZA]
""")
        
        logger.info(f"Fallback belge oluşturuldu, uzunluk: {len(result)}")
        return result

    def _generate_multi_document_based_text(self, combined_content, document_type, additional_instructions, file_summaries):
        """Çoklu belgeye dayalı AI metin üretimi"""
        try:
            logger.info(f"Çoklu belge AI üretimi başlıyor - Tür: {document_type}")
            
            # Eğer Gemini çalışmıyorsa direkt fallback kullan
            if not hasattr(self, 'gemini_model') or self.gemini_model is None:
                logger.warning("Gemini model bulunamadı, fallback kullanılıyor")
                return self._generate_multi_document_fallback(document_type, file_summaries, additional_instructions)
            
            # Çoklu belge analizi için özel prompt
            analysis_prompt = f"""
            Aşağıdaki {len(file_summaries)} hukuki belgeyi analiz et ve önemli bilgileri çıkar:
            
            BELGELER:
            {combined_content[:4000]}  # İlk 4000 karakter
            
            DOSYA BİLGİLERİ:
            {chr(10).join([f"- {f['name']} ({f['type']}, {f['length']} karakter)" for f in file_summaries])}
            
            Analiz et:
            1. Her belgenin türü ve amacı
            2. Belgeler arasındaki ilişki
            3. Ana taraflar ve rolleri
            4. Önemli tarihler ve süreçler
            5. Para miktarları ve talep edilen hususlar
            6. Hukuki gerekçeler ve dayanaklar
            7. Mahkeme bilgileri ve süreç durumu
            
            Analiz sonucunu detaylı JSON formatında ver.
            """
            
            logger.info("Gemini çoklu belge analizi başlatılıyor...")
            try:
                analysis_response = self.gemini_model.generate_content(analysis_prompt)
                logger.info(f"Analiz tamamlandı, uzunluk: {len(analysis_response.text) if analysis_response.text else 0}")
            except Exception as e:
                logger.error(f"Gemini analiz hatası: {str(e)}")
                return self._generate_multi_document_fallback(document_type, file_summaries, additional_instructions)
            
            # Üretim prompt'u hazırla
            generation_prompt = self._build_multi_document_prompt(
                combined_content, document_type, analysis_response.text, additional_instructions, file_summaries
            )
            
            logger.info("Gemini çoklu belge üretimi başlatılıyor...")
            try:
                generation_response = self.gemini_model.generate_content(generation_prompt)
                
                if generation_response.text and len(generation_response.text.strip()) > 100:
                    logger.info(f"Çoklu belge üretimi başarılı, uzunluk: {len(generation_response.text)}")
                    return generation_response.text
                else:
                    logger.warning("Gemini boş/yetersiz yanıt verdi, fallback kullanılıyor")
                    return self._generate_multi_document_fallback(document_type, file_summaries, additional_instructions)
                    
            except Exception as e:
                logger.error(f"Gemini üretim hatası: {str(e)}")
                return self._generate_multi_document_fallback(document_type, file_summaries, additional_instructions)
            
        except Exception as e:
            logger.error(f"Multi-document AI generation error: {str(e)}", exc_info=True)
            return self._generate_multi_document_fallback(document_type, file_summaries, additional_instructions)

    def _build_multi_document_prompt(self, combined_content, document_type, analysis, additional_instructions, file_summaries):
        """Çoklu belge için üretim prompt'u oluştur"""
        
        base_prompt = f"""
        Sen bir uzman hukuk danışmanısın. {len(file_summaries)} adet belgeye istinaden "{document_type}" hazırlayacaksın.
        
        KAYNAK BELGELER ANALİZİ:
        {analysis}
        
        KAYNAK BELGELER İÇERİĞİ:
        {combined_content[:3000]}
        
        DOSYA LİSTESİ:
        {chr(10).join([f"- {f['name']}" for f in file_summaries])}
        """
        
        if additional_instructions:
            base_prompt += f"""
        
        ÖZEL TALİMATLAR:
        {additional_instructions}
        """
        
        base_prompt += f"""
        
        ÜRETİLECEK BELGE: {document_type}
        
        Aşağıdaki kriterlere uygun belge hazırla:
        - Türk hukuk sistemine uygun format ve terminoloji
        - Tüm kaynak belgelerdeki bilgileri dikkate al
        - Profesyonel ve hukuki standartlara uygun. Asterisk (*) kullanma, vurgu için BÜYÜK HARF kullan
        - Gerekli madde referansları ve hukuki dayanaklar
        - Net ve anlaşılır dil. Markdown formatı değil, düz metin kullan
        - Yaklaşık 400-600 kelime
        - Belge türüne uygun başlık ve format
        - Tarih ve imza alanları
        - İlgili tarafların doğru şekilde belirtilmesi
        
        ÖZEL DİKKAT:
        - Tüm kaynak belgelerdeki önemli bilgileri harmanlayarak tutarlı bir {document_type} oluştur
        - Belgeler arasındaki çelişkiler varsa bunları belirt
        - Eksik bilgiler için [BELİRTİLECEK] notasyonu kullan
        """
        
        return base_prompt

    def _generate_multi_document_fallback(self, document_type, file_summaries, additional_instructions):
        """Çoklu belge için fallback üretici"""
        logger.info(f"Çoklu belge fallback üretiliyor - Tür: {document_type}")
        
        file_list = "\n".join([f"- {f['name']}" for f in file_summaries])
        
        fallback_text = f"""{document_type.upper()}

SAYIN MAHKEME BAŞKANLIĞINA / İLGİLİ MAKAMA

KAYNAK BELGELER:
{file_list}

SAYGILI MAKAMİNİZ,

Ekli {len(file_summaries)} adet belgeye istinaden hazırlanan bu {document_type} ile aşağıdaki hususları arz ederim:

1. GENEL BİLGİLER:
[Kaynak belgelerden çıkarılan genel bilgiler]

2. HUKUKİ DEĞERLENDİRME:
[Hukuki analiz ve değerlendirme]

3. TALEBİMİZ:
[Talep edilen hususlar]
"""

        if additional_instructions:
            fallback_text += f"""

ÖZEL HUSUSLAR:
{additional_instructions}
"""

        fallback_text += f"""

Bu nedenlerle talebimin kabulüne karar verilmesini saygılarımla arz ederim.

{datetime.now().strftime('%d/%m/%Y')}

[İMZA]
[ADI SOYADI]
[SİFATI]
"""
        
        logger.info(f"Çoklu belge fallback oluşturuldu, uzunluk: {len(fallback_text)}")
        return fallback_text

    def get_template_fields(self, template_type, subtype=None):
        """Şablon için gerekli alanları getir"""
        if template_type not in self.templates:
            return None
        
        template = self.templates[template_type]
        fields = template['required_fields'].copy()
        
        # Alt türe göre ek alanlar
        if subtype:
            additional_fields = self._get_subtype_fields(template_type, subtype)
            fields.extend(additional_fields)
        
        return {
            'name': template['name'],
            'description': template['description'],
            'subtypes': template['subtypes'],
            'fields': fields
        }

    def generate_document(self, template_type, parameters, user=None):
        """Belge üret"""
        try:
            if template_type not in self.templates:
                return {
                    'success': False,
                    'error': 'Geçersiz şablon türü'
                }
            
            # Parametreleri kontrol et
            validation_result = self._validate_parameters(template_type, parameters)
            if not validation_result['valid']:
                return {
                    'success': False,
                    'error': f"Eksik alanlar: {', '.join(validation_result['missing_fields'])}"
                }
            
            # Belgeyi oluştur
            generated_text = self._generate_text(template_type, parameters)
            
            # Yıldızları temizle
            generated_text = self.clean_asterisks(generated_text)
            
            # Meta bilgileri ekle
            metadata = {
                'template_type': template_type,
                'generation_date': datetime.now().isoformat(),
                'word_count': len(generated_text.split()),
                'user_id': user.id if user else None
            }
            
            return {
                'success': True,
                'document': {
                    'content': self.clean_asterisks(generated_text),
                    'metadata': metadata,
                    'template_name': self.templates[template_type]['name']
                }
            }
            
        except Exception as e:
            logger.error(f"Legal text generation error: {str(e)}")
            return {
                'success': False,
                'error': 'Metin üretimi sırasında bir hata oluştu'
            }

    def _validate_parameters(self, template_type, parameters):
        """Parametre doğrulama"""
        template = self.templates[template_type]
        required_fields = template['required_fields']
        missing_fields = []
        
        for field in required_fields:
            if field not in parameters or not parameters[field].strip():
                missing_fields.append(field)
        
        return {
            'valid': len(missing_fields) == 0,
            'missing_fields': missing_fields
        }

    def _get_subtype_fields(self, template_type, subtype):
        """Alt tür için ek alanlar"""
        subtype_fields = {
            'dilekce': {
                'alacak': ['alacak_miktari', 'vade'],
                'boşanma': ['evlilik_tarihi', 'cocuk_sayisi'],
                'iş': ['işe_başlama', 'maaş'],
                'miras': ['ölen_kişi', 'miras_payı'],
                'tapu': ['ada_parsel', 'metre_kare']
            },
            'sozlesme': {
                'satış': ['eşya', 'teslim_yeri'],
                'kira': ['emlak_adresi', 'depozito'],
                'iş': ['pozisyon', 'maaş'],
                'ortaklık': ['sermaye', 'pay_oranı'],
                'hizmet': ['hizmet_türü', 'süre']
            }
        }
        
        return subtype_fields.get(template_type, {}).get(subtype, [])

    def _generate_text(self, template_type, parameters):
        """Ana metin üretimi"""
        generators = {
            'dilekce': self._generate_petition,
            'sozlesme': self._generate_contract,
            'gorus': self._generate_opinion,
            'cevap': self._generate_response,
            'temyiz': self._generate_appeal
        }
        
        generator = generators.get(template_type)
        if generator:
            return generator(parameters)
        else:
            return "Şablon üreticisi bulunamadı."

    def _generate_petition(self, params):
        """Dilekçe üretici"""
        subtype = params.get('subtype', 'genel')
        
        if subtype == 'alacak':
            return self._generate_debt_petition(params)
        elif subtype == 'boşanma':
            return self._generate_divorce_petition(params)
        elif subtype == 'iş':
            return self._generate_labor_petition(params)
        else:
            return self._generate_general_petition(params)

    def _generate_debt_petition(self, params):
        """Alacak davası dilekçesi"""
        template = f"""
{params.get('mahkeme', 'SAYGI DEĞER MAHKEME').upper()} BAŞKANLIĞINA

DAVACI: {params.get('davaci', '[DAVACI ADI]')}

DAVALI: {params.get('davali', '[DAVALI ADI]')}

DAVA KONUSU: {params.get('konu', 'Alacak Davası')}

DAVA DEĞERİ: {params.get('alacak_miktari', '[TUTAR]')} TL

SAYGILI MAHKEME BAŞKANLIĞI,

Davalı ile aramızda {params.get('tarih', '[TARİH]')} tarihinde yapılan {params.get('işlem', 'işlem')} gereğince, davalının tarafıma {params.get('alacak_miktari', '[TUTAR]')} TL tutarında borcu bulunmaktadır.

Bu alacağım {params.get('vade', '[VADE TARİHİ]')} tarihinde muaccel hale gelmiş olup, davalıya usulünce ihtarda bulunulmasına rağmen borcunu ödememiştir.

Bu nedenlerle;

1- Davalıdan {params.get('alacak_miktari', '[TUTAR]')} TL ana para,
2- Bu tutara {params.get('vade', '[VADE TARİHİ]')} tarihinden itibaren hesaplanacak yasal faiz,
3- Yargılama giderleri ve vekalet ücretinin davalıdan tahsiline,

KARAR VERİLMESİNİ saygılarımla arz ve talep ederim.

{datetime.now().strftime('%d/%m/%Y')}

                                                    DAVACI VEKİLİ
                                        {params.get('vekil', '[VEKİL ADI]')}
"""
        return template.strip()

    def _generate_divorce_petition(self, params):
        """Boşanma davası dilekçesi"""
        template = f"""
{params.get('mahkeme', 'SAYIN AİLE MAHKEMESİ').upper()} BAŞKANLIĞINA

DAVACI: {params.get('davaci', '[DAVACI ADI]')}

DAVALI: {params.get('davali', '[DAVALI ADI]')}

DAVA KONUSU: Boşanma

SAYGILI MAHKEME BAŞKANLIĞI,

Taraflar {params.get('evlilik_tarihi', '[EVLİLİK TARİHİ]')} tarihinde evlenmiş olup, evliliklerinden {params.get('cocuk_sayisi', '0')} çocuk dünyaya gelmiştir.

Evliliğimizin devamı süresince davalının davranışları nedeniyle evlilik birliği temelinden sarsılmış, ortak hayat dayanılmaz hale gelmiştir.

{params.get('bosanma_sebebi', 'Evlilik birliği temelinden sarsılmıştır.')}"

Bu nedenlerle;

1- TMK 166. madde uyarınca tarafların boşanmasına,
2- Ortak çocuğun velayetinin tarafıma bırakılmasına,
3- Çocuğun nafakasına,
4- Yargılama giderleri ve vekalet ücretinin davalıdan tahsiline,

KARAR VERİLMESİNİ saygılarımla arz ve talep ederim.

{datetime.now().strftime('%d/%m/%Y')}

                                                    DAVACI VEKİLİ
                                        {params.get('vekil', '[VEKİL ADI]')}
"""
        return template.strip()

    def _generate_general_petition(self, params):
        """Genel dilekçe"""
        template = f"""
{params.get('mahkeme', 'SAYGI DEĞER MAHKEME').upper()} BAŞKANLIĞINA

DAVACI: {params.get('davaci', '[DAVACI ADI]')}

DAVALI: {params.get('davali', '[DAVALI ADI]')}

DAVA KONUSU: {params.get('konu', '[DAVA KONUSU]')}

SAYGILI MAHKEME BAŞKANLIĞI,

{params.get('olay', 'Olay açıklaması buraya yazılacaktır.')}

{params.get('hukuki_dayanak', 'Hukuki dayanaklar buraya yazılacaktır.')}

Bu nedenlerle;

{params.get('talep', 'Talep edilen hususlar buraya yazılacaktır.')}

KARAR VERİLMESİNİ saygılarımla arz ve talep ederim.

{datetime.now().strftime('%d/%m/%Y')}

                                                    DAVACI VEKİLİ
                                        {params.get('vekil', '[VEKİL ADI]')}
"""
        return template.strip()

    def _generate_contract(self, params):
        """Sözleşme üretici"""
        subtype = params.get('subtype', 'genel')
        
        if subtype == 'satış':
            return self._generate_sales_contract(params)
        elif subtype == 'kira':
            return self._generate_rental_contract(params)
        else:
            return self._generate_general_contract(params)

    def _generate_sales_contract(self, params):
        """Satış sözleşmesi"""
        template = f"""
SATIŞ SÖZLEŞMESİ

SATICI: {params.get('taraf1', '[SATICI ADI]')}

ALICI: {params.get('taraf2', '[ALICI ADI]')}

Yukarıda kimlik bilgileri yazılı taraflar arasında aşağıdaki şartlarda satış sözleşmesi akdedilmiştir.

MADDE 1- SATIŞ KONUSU
Satıcı, {params.get('eşya', '[EŞYA TANIMI]')} satmayı, alıcı da satın almayı kabul etmiştir.

MADDE 2- SATIŞ BEDELİ
Satış bedeli {params.get('bedel', '[TUTAR]')} TL olarak belirlenmiştir.

MADDE 3- ÖDEME ŞARTLARI
Bedel {params.get('odeme_sekli', 'peşin olarak')} ödenecektir.

MADDE 4- TESLİM
Satış konusu eşya {params.get('teslim_yeri', '[TESLİM YERİ]')} teslim edilecektir.

MADDE 5- GARANTİ
{params.get('garanti', 'Garanti şartları belirtilecektir.')}

Bu sözleşme {datetime.now().strftime('%d/%m/%Y')} tarihinde 2 nüsha olarak düzenlenmiş ve taraflarca imzalanmıştır.

SATICI                                    ALICI
{params.get('taraf1', '[SATICI ADI]')}         {params.get('taraf2', '[ALICI ADI]')}
"""
        return template.strip()

    def _generate_rental_contract(self, params):
        """Kira sözleşmesi"""
        template = f"""
KİRA SÖZLEŞMESİ

KİRALAYAN: {params.get('taraf1', '[KİRALAYAN ADI]')}

KİRACI: {params.get('taraf2', '[KİRACI ADI]')}

MADDE 1- KİRA KONUSU
Kiralayan, {params.get('emlak_adresi', '[EMLAK ADRESİ]')} adresindeki {params.get('emlak_türü', 'daire')}yi kiralamıştır.

MADDE 2- KİRA BEDELİ
Aylık kira bedeli {params.get('bedel', '[TUTAR]')} TL'dir.

MADDE 3- SÜRESİ
Kira süresi {params.get('süre', '[SÜRE]')} olarak belirlenmiştir.

MADDE 4- DEPOZİTO
Depozito olarak {params.get('depozito', '[DEPOZİTO TUTARI]')} TL alınmıştır.

MADDE 5- KİRACI YÜKÜMLÜLÜKLERİ
{params.get('yukumlululer', 'Kiracı yükümlülükleri belirtilecektir.')}

Bu sözleşme {datetime.now().strftime('%d/%m/%Y')} tarihinde düzenlenmiştir.

KİRALAYAN                                KİRACI
{params.get('taraf1', '[KİRALAYAN]')}         {params.get('taraf2', '[KİRACI]')}
"""
        return template.strip()

    def _generate_general_contract(self, params):
        """Genel sözleşme"""
        template = f"""
SÖZLEŞME

TARAF 1: {params.get('taraf1', '[TARAF 1 ADI]')}

TARAF 2: {params.get('taraf2', '[TARAF 2 ADI]')}

MADDE 1- KONU
{params.get('konu', 'Sözleşme konusu belirtilecektir.')}

MADDE 2- ŞARTLAR
{params.get('şartlar', 'Sözleşme şartları belirtilecektir.')}

MADDE 3- SÜRESİ
Sözleşme süresi {params.get('süre', '[SÜRE]')} olarak belirlenmiştir.

MADDE 4- GENEL HÜKÜMLER
{params.get('genel_hukumler', 'Genel hükümler belirtilecektir.')}

{datetime.now().strftime('%d/%m/%Y')}

TARAF 1                                  TARAF 2
{params.get('taraf1', '[TARAF 1]')}           {params.get('taraf2', '[TARAF 2]')}
"""
        return template.strip()

    def _generate_opinion(self, params):
        """Hukuki görüş"""
        template = f"""
HUKUKİ GÖRÜŞ

KONU: {params.get('konu', '[GÖRÜŞ KONUSU]')}

1. OLAY ÖZETİ
{params.get('olay', 'Olay özetinin yazılacağı alan.')}

2. HUKUKİ DEĞERLENDİRME
{params.get('degerlendirme', 'Hukuki değerlendirmenin yazılacağı alan.')}

3. İLGİLİ MEVZUAT
{params.get('mevzuat', 'İlgili mevzuatın belirtileceği alan.')}

4. SONUÇ
{params.get('sonuc', 'Sonuç ve görüşün yazılacağı alan.')}

{datetime.now().strftime('%d/%m/%Y')}

Av. {params.get('hazirlayan', '[HAZ RLAYAN AVUKAT]')}
"""
        return template.strip()

    def _generate_response(self, params):
        """Cevap dilekçesi"""
        template = f"""
CEVAP DİLEKÇESİ

{params.get('mahkeme', 'SAYGI DEĞER MAHKEME').upper()} BAŞKANLIĞINA

DAVA NO: {params.get('dava_no', '[DAVA NUMARASI]')}

DAVALININ CEVABI

SAYGILI MAHKEME BAŞKANLIĞI,

Davacının {params.get('dava_tarihi', '[DAVA TARİHİ]')} tarihli dilekçesi ile açtığı dava hakkında aşağıdaki cevaplarımı sunarım:

{params.get('savunma', 'Savunma yazılacak alan.')}

Bu nedenlerle;

Davanın reddine karar verilmesini saygılarımla arz ederim.

{datetime.now().strftime('%d/%m/%Y')}

                                                    DAVALI VEKİLİ
                                        {params.get('vekil', '[VEKİL ADI]')}
"""
        return template.strip()

    def _generate_appeal(self, params):
        """Temyiz dilekçesi"""
        template = f"""
TEMYİZ DİLEKÇESİ

YARGITAY {params.get('daire', '[DAİRE]')}. HUKUK DAİRESİ BAŞKANLIĞINA

KARAR VEREN MAHKEME: {params.get('mahkeme', '[MAHKEME ADI]')}
KARAR TARİHİ: {params.get('karar_tarihi', '[KARAR TARİHİ]')}
KARAR NO: {params.get('karar_no', '[KARAR NUMARASI]')}

TEMYİZ EDEN: {params.get('temyiz_eden', '[TEMYİZ EDEN ADI]')}

SAYGILI YARGITAY BAŞKANLIĞI,

Yukarıda tarih ve numarası yazılı mahkeme kararına karşı aşağıdaki gerekçelerle temyiz başvurusunda bulunuyorum:

TEMYİZ NEDENLERİ:
{params.get('temyiz_nedeni', 'Temyiz nedenlerinin yazılacağı alan.')}

Bu nedenlerle, bozma kararı verilmesini saygılarımla arz ederim.

{datetime.now().strftime('%d/%m/%Y')}

                                                    VEKİL
                                        {params.get('vekil', '[VEKİL ADI]')}
"""
        return template.strip()
    def clean_markdown_formatting(self, text):
        """Metindeki markdown formatlamasını temizle"""
        import re
        
        if not text:
            return text
            
        # **bold** -> BÜYÜK HARF
        text = re.sub(r'\*\*(.*?)\*\*', lambda m: m.group(1).upper(), text)
        
        # *italic* -> Normal metin
        text = re.sub(r'(?<\!\*)\*([^*]+)\*(?\!\*)', r'\1', text)
        
        # Tek * işaretlerini temizle
        text = re.sub(r'(?<\!\w)\*(?\!\w)', '', text)
        
        # ### Başlık -> BAŞLIK
        text = re.sub(r'^#{1,6}\s*(.*)', lambda m: m.group(1).upper(), text, flags=re.MULTILINE)
        
        # - Liste öğesi -> • Liste öğesi
        text = re.sub(r'^\s*-\s*', '• ', text, flags=re.MULTILINE)
        
        return text.strip()
