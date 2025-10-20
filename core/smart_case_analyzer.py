# core/smart_case_analyzer.py

import re
import os
import pickle
import faiss
import numpy as np
import logging
from django.core.cache import cache
from django.conf import settings
from .models import JudicialDecision, Legislation
from .ai_legal_assistant import AILegalAssistant
from sentence_transformers import SentenceTransformer
import datetime

logger = logging.getLogger(__name__)

class SmartCaseAnalyzer:
    """Akıllı Dava Dosyası Analizi - PDF dava dosyalarını analiz eder"""
    
    def __init__(self):
        # FAISS dizinleri için yol
        self.faiss_dir = os.path.join(settings.BASE_DIR, 'faiss_dizinleri')
        self.embedding_model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
        self._loaded_indexes = {}
        self.document_patterns = {
            'dilekçe': [r'dilekçe', r'dava dilekçesi', r'başvuru', r'talep'],
            'vekalet': [r'vekalet', r'vekaletname', r'vekil'],
            'kimlik': [r'kimlik', r'nüfus cüzdanı', r'tc kimlik'],
            'evrak': [r'mahkeme', r'dosya no', r'dava no'],
            'belge': [r'senet', r'sözleşme', r'fatura', r'makbuz'],
            'tanık': [r'tanık', r'şahit listesi', r'ifade'],
            'bilirkişi': [r'bilirkişi', r'ekspertiz', r'rapor'],
            'karar': [r'karar', r'hüküm', r'mahkeme kararı']
        }
        
        self.case_types = {
            'boşanma': [r'boşanma', r'ayrılık', r'nafaka', r'velayet', r'aile mahkemesi'],
            'alacak': [r'alacak', r'borç', r'ödeme', r'tazminat', r'icra'],
            'iş': [r'işçi', r'işveren', r'kıdem', r'işten çıkarma', r'iş mahkemesi'],
            'miras': [r'miras', r'veraset', r'tereeke', r'mirasçı'],
            'ceza': [r'ceza', r'suç', r'sanık', r'mağdur', r'ceza mahkemesi'],
            'ticaret': [r'ticaret', r'şirket', r'ortaklık', r'ticari'],
            'tapu': [r'tapu', r'mülkiyet', r'gayrimenkul', r'arsa', r'daire'],
            'trafik': [r'trafik', r'araç', r'kaza', r'sigorta'],
            'idari': [r'idari', r'belediye', r'kamu', r'memur', r'danıştay']
        }
        
        self.legal_concepts = {
            'zamanaşımı': [r'zamanaşımı', r'zaman aşımı', r'süre'],
            'delil': [r'delil', r'ispat', r'kanıt', r'belge'],
            'yargılama_gideri': [r'harç', r'gider', r'avukatlık ücreti', r'masraf'],
            'temyiz': [r'temyiz', r'istinaf', r'karar düzeltme'],
            'ihtiyati_tedbir': [r'ihtiyati tedbir', r'geçici hukuki koruma'],
            'vasi': [r'vasi', r'vesayet', r'küçük', r'mahcur']
        }

    def analyze_case_document(self, file_text, user=None):
        """Ana analiz fonksiyonu"""
        try:
            logger.info(f"Dava dosyası analizi başlıyor - Metin uzunluğu: {len(file_text)} karakter")
            logger.info(f"Metin önizleme (ilk 200 karakter): {repr(file_text[:200])}")
            
            # Cache kontrolü
            cache_key = f"case_analysis_{hash(file_text[:1000])}"
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.info("Cache'den analiz sonucu döndürülüyor")
                return cached_result
            
            # Temel analiz
            logger.info("Doküman bilgisi çıkarılıyor...")
            document_info = self._extract_document_info(file_text)
            logger.info(f"Doküman türü: {document_info.get('document_type', 'Bilinmeyen')}")
            
            logger.info("Dava türü tespit ediliyor...")
            case_type = self._identify_case_type(file_text)
            logger.info(f"Tespit edilen dava türü: {case_type.get('type', 'Bilinmeyen')} (güven: {case_type.get('confidence', 0)}%)")
            
            logger.info("Eksik belgeler kontrol ediliyor...")
            missing_documents = self._check_missing_documents(file_text, case_type)
            logger.info(f"Eksik belge sayısı: {missing_documents.get('total_missing', 0)}")
            
            logger.info("Hukuki konular tespit ediliyor...")
            legal_issues = self._identify_legal_issues(file_text)
            logger.info(f"Tespit edilen hukuki konu sayısı: {len(legal_issues)}")
            
            logger.info("İlgili mevzuat aranıyor...")
            relevant_laws = self._find_relevant_laws(file_text, case_type)
            logger.info(f"İlgili mevzuat sayısı: {len(relevant_laws)}")
            
            logger.info("Benzer davalar aranıyor...")
            similar_cases = self._find_similar_cases(case_type, legal_issues, file_text)
            logger.info(f"Bulunan benzer dava sayısı: {len(similar_cases)}")
            
            logger.info("Öneriler hazırlanıyor...")
            recommendations = self._generate_recommendations(case_type, missing_documents, legal_issues, file_text)
            logger.info(f"Hazırlanan öneri sayısı: {len(recommendations)}")
            
            result = {
                'success': True,
                'analysis': {
                    'document_info': document_info,
                    'case_type': case_type,
                    'missing_documents': missing_documents,
                    'legal_issues': legal_issues,
                    'relevant_laws': relevant_laws,
                    'similar_cases': similar_cases,
                    'recommendations': recommendations,
                    'analysis_date': datetime.datetime.now().isoformat()
                }
            }
            
            # Cache'e kaydet
            cache.set(cache_key, result, 1800)  # 30 dakika
            
            return result
            
        except Exception as e:
            logger.error(f"Case analysis error: {str(e)}")
            return {
                'success': False,
                'error': 'Dosya analizi sırasında bir hata oluştu.'
            }

    def _extract_document_info(self, text):
        """Belge bilgilerini çıkar"""
        info = {
            'page_count': text.count('\n\n') + 1,  # Tahmini sayfa sayısı
            'word_count': len(text.split()),
            'document_type': 'Bilinmeyen',
            'parties': [],
            'case_number': None,
            'court': None,
            'date': None
        }
        
        # Belge türünü tespit et
        for doc_type, patterns in self.document_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    info['document_type'] = doc_type.title()
                    break
        
        # Dava numarasını bul
        case_num_pattern = r'(?:dava|dosya)\s*(?:no|numarası)?\s*:?\s*(\d{4}/\d+|\d+/\d+)'
        case_match = re.search(case_num_pattern, text, re.IGNORECASE)
        if case_match:
            info['case_number'] = case_match.group(1)
        
        # Mahkeme bilgisini bul
        court_pattern = r'(\w+\s*mahkemesi|\w+\s*mahkemesi\s*\w+\s*hukuk\s*dairesi)'
        court_match = re.search(court_pattern, text, re.IGNORECASE)
        if court_match:
            info['court'] = court_match.group(1)
        
        # Tarih bilgisini bul
        date_pattern = r'(\d{1,2}[/.]\d{1,2}[/.]\d{4}|\d{4}[/.]\d{1,2}[/.]\d{1,2})'
        date_match = re.search(date_pattern, text)
        if date_match:
            info['date'] = date_match.group(1)
        
        # Tarafları bul (basit yaklaşım)
        if 'davacı' in text.lower():
            info['parties'].append('Davacı')
        if 'davalı' in text.lower():
            info['parties'].append('Davalı')
        if 'başvurucu' in text.lower():
            info['parties'].append('Başvurucu')
        
        return info

    def _identify_case_type(self, text):
        """Dava türünü tespit et"""
        max_score = 0
        identified_type = 'genel'
        
        for case_type, patterns in self.case_types.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, text, re.IGNORECASE))
                score += matches
            
            if score > max_score:
                max_score = score
                identified_type = case_type
        
        confidence = min(max_score * 10, 100)  # Güven skoru
        
        return {
            'type': identified_type,
            'confidence': confidence,
            'description': self._get_case_type_description(identified_type)
        }

    def _get_case_type_description(self, case_type):
        """Dava türü açıklaması"""
        descriptions = {
            'boşanma': 'Aile hukuku kapsamında boşanma davası',
            'alacak': 'Borçlar hukuku kapsamında alacak davası',
            'iş': 'İş hukuku kapsamında işçi-işveren uyuşmazlığı',
            'miras': 'Miras hukuku kapsamında veraset davası',
            'ceza': 'Ceza hukuku kapsamında ceza davası',
            'ticaret': 'Ticaret hukuku kapsamında ticari uyuşmazlık',
            'tapu': 'Eşya hukuku kapsamında mülkiyet davası',
            'trafik': 'Trafik kazası tazminat davası',
            'idari': 'İdare hukuku kapsamında idari uyuşmazlık',
            'genel': 'Genel hukuki uyuşmazlık'
        }
        
        return descriptions.get(case_type, 'Belirtilmemiş')

    def _check_missing_documents(self, text, case_type_info):
        """Eksik belgeleri tespit et - Geliştirilmiş delil analizi"""
        case_type = case_type_info['type']
        found_documents = []
        missing_documents = []
        
        # Mevcut belgeleri tespit et
        for doc_type, patterns in self.document_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    found_documents.append(doc_type)
                    break
        
        # Dava türüne göre gerekli belgeler - Genişletilmiş liste
        required_docs = {
            'boşanma': [
                {'doc': 'dilekçe', 'importance': 'Kritik', 'reason': 'Dava açmak için zorunlu'},
                {'doc': 'vekalet', 'importance': 'Yüksek', 'reason': 'Avukat temsili için gerekli'},
                {'doc': 'kimlik', 'importance': 'Kritik', 'reason': 'Kimlik tespiti için zorunlu'},
                {'doc': 'evlilik cüzdanı', 'importance': 'Kritik', 'reason': 'Evlilik ispatı için zorunlu'},
                {'doc': 'gelir belgesi', 'importance': 'Yüksek', 'reason': 'Nafaka hesabı için gerekli'},
                {'doc': 'çocuk nüfus kaydı', 'importance': 'Yüksek', 'reason': 'Velayet kararı için gerekli'},
                {'doc': 'evlilik fotoğrafları', 'importance': 'Orta', 'reason': 'Evlilik birliğinin ispatı için'},
                {'doc': 'tanık listesi', 'importance': 'Orta', 'reason': 'Boşanma sebeplerinin ispatı için'},
                {'doc': 'şiddet raporu', 'importance': 'Yüksek', 'reason': 'Şiddet iddiası varsa kritik'},
                {'doc': 'psikoloji raporu', 'importance': 'Orta', 'reason': 'Çocuğun durumu için'}
            ],
            'alacak': [
                {'doc': 'dilekçe', 'importance': 'Kritik', 'reason': 'Dava açmak için zorunlu'},
                {'doc': 'vekalet', 'importance': 'Yüksek', 'reason': 'Avukat temsili için gerekli'},
                {'doc': 'kimlik', 'importance': 'Kritik', 'reason': 'Kimlik tespiti için zorunlu'},
                {'doc': 'senet', 'importance': 'Kritik', 'reason': 'Alacağın temel dayanağı'},
                {'doc': 'fatura', 'importance': 'Yüksek', 'reason': 'Mal/hizmet teslimatının ispatı'},
                {'doc': 'ödeme planı', 'importance': 'Orta', 'reason': 'Vade şartlarının belirlenmesi'},
                {'doc': 'ihtarname', 'importance': 'Yüksek', 'reason': 'Temerrüt halinin ispatı'},
                {'doc': 'banka hesap dökümü', 'importance': 'Orta', 'reason': 'Ödeme durumunun kontrolü'},
                {'doc': 'tanık beyanı', 'importance': 'Orta', 'reason': 'Alacağın doğrulanması için'},
                {'doc': 'ekspertiz raporu', 'importance': 'Orta', 'reason': 'Mal/hizmet kalitesi için'}
            ],
            'iş': [
                {'doc': 'dilekçe', 'importance': 'Kritik', 'reason': 'Dava açmak için zorunlu'},
                {'doc': 'vekalet', 'importance': 'Yüksek', 'reason': 'Avukat temsili için gerekli'},
                {'doc': 'kimlik', 'importance': 'Kritik', 'reason': 'Kimlik tespiti için zorunlu'},
                {'doc': 'iş sözleşmesi', 'importance': 'Kritik', 'reason': 'İş ilişkisinin temel belgesi'},
                {'doc': 'bordro', 'importance': 'Yüksek', 'reason': 'Maaş ve hakların ispatı'},
                {'doc': 'işten çıkarma yazısı', 'importance': 'Kritik', 'reason': 'İşten çıkarma gerekçelerinin incelenmesi'},
                {'doc': 'SGK kayıtları', 'importance': 'Yüksek', 'reason': 'Çalışma sürelerinin ispatı'},
                {'doc': 'tanık listesi', 'importance': 'Orta', 'reason': 'Çalışma koşullarının ispatı'},
                {'doc': 'performans değerlendirmesi', 'importance': 'Orta', 'reason': 'İş performansının belgelenmesi'},
                {'doc': 'disiplin kurulu kararı', 'importance': 'Yüksek', 'reason': 'Disiplin işlemlerinin incelenmesi'}
            ],
            'miras': [
                {'doc': 'dilekçe', 'importance': 'Kritik', 'reason': 'Dava açmak için zorunlu'},
                {'doc': 'vekalet', 'importance': 'Yüksek', 'reason': 'Avukat temsili için gerekli'},
                {'doc': 'kimlik', 'importance': 'Kritik', 'reason': 'Kimlik tespiti için zorunlu'},
                {'doc': 'ölüm belgesi', 'importance': 'Kritik', 'reason': 'Ölüm vakıasının ispatı'},
                {'doc': 'veraset ilamı', 'importance': 'Kritik', 'reason': 'Mirasçılık sıfatının ispatı'},
                {'doc': 'nüfus kayıtları', 'importance': 'Yüksek', 'reason': 'Aile bağının ispatı'},
                {'doc': 'vasiyet', 'importance': 'Yüksek', 'reason': 'Vasiyetin varlığının kontrolü'},
                {'doc': 'tapu kayıtları', 'importance': 'Yüksek', 'reason': 'Gayrimenkul miras payı için'},
                {'doc': 'banka hesap dökümü', 'importance': 'Orta', 'reason': 'Miras değerinin tespiti'},
                {'doc': 'değer takdir raporu', 'importance': 'Orta', 'reason': 'Miras değerinin belirlenmesi'}
            ],
            'genel': [
                {'doc': 'dilekçe', 'importance': 'Kritik', 'reason': 'Dava açmak için zorunlu'},
                {'doc': 'vekalet', 'importance': 'Yüksek', 'reason': 'Avukat temsili için gerekli'},
                {'doc': 'kimlik', 'importance': 'Kritik', 'reason': 'Kimlik tespiti için zorunlu'}
            ]
        }
        
        case_required = required_docs.get(case_type, required_docs['genel'])
        
        for required_doc in case_required:
            doc_name = required_doc['doc']
            if doc_name not in found_documents:
                missing_documents.append({
                    'document': doc_name,
                    'importance': required_doc['importance'],
                    'reason': required_doc['reason'],
                    'description': self._get_document_description(doc_name)
                })
        
        return {
            'found': found_documents,
            'missing': missing_documents,
            'total_found': len(found_documents),
            'total_missing': len(missing_documents)
        }

    def _get_document_description(self, document):
        """Belge açıklaması"""
        descriptions = {
            'dilekçe': 'Dava dilekçesi - Davanın temel belgesi',
            'vekalet': 'Vekaletname - Avukat için gerekli',
            'kimlik': 'TC Kimlik belgesi - Kimlik tespiti için',
            'evlilik cüzdanı': 'Evlilik cüzdanı - Evlilik ispatı için',
            'gelir belgesi': 'Gelir belgesi - Nafaka hesabı için',
            'senet': 'Borç senedi - Alacağın ispatı için',
            'fatura': 'Fatura/makbuz - Ödeme ispatı için',
            'iş sözleşmesi': 'İş sözleşmesi - İş ilişkisinin ispatı için',
            'bordro': 'Maaş bordrosu - Gelir ispatı için',
            'ölüm belgesi': 'Ölüm belgesi - Ölüm ispatı için',
            'veraset ilamı': 'Veraset ilamı - Mirasçılık ispatı için',
            'tapu': 'Tapu senedi - Mülkiyet ispatı için'
        }
        
        return descriptions.get(document, 'Belge açıklaması mevcut değil')

    def _identify_legal_issues(self, text):
        """Hukuki konuları tespit et"""
        issues = []
        
        for concept, patterns in self.legal_concepts.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    issues.append({
                        'concept': concept,
                        'description': self._get_legal_concept_description(concept),
                        'importance': 'Yüksek'
                    })
                    break
        
        return issues

    def _get_legal_concept_description(self, concept):
        """Hukuki kavram açıklaması"""
        descriptions = {
            'zamanaşımı': 'Belirli süre geçmesi ile hakkın düşmesi',
            'delil': 'İddiaların ispatı için gerekli belgeler',
            'yargılama_gideri': 'Dava sürecindeki masraflar',
            'temyiz': 'Kararın üst mahkemede incelenmesi',
            'ihtiyati_tedbir': 'Geçici koruma önlemleri',
            'vasi': 'Küçük ve kısıtlıların hukuki temsilcisi'
        }
        
        return descriptions.get(concept, 'Açıklama mevcut değil')

    def _find_relevant_laws(self, text, case_type_info):
        """İlgili mevzuatı bul"""
        case_type = case_type_info['type']
        relevant_laws = []
        
        # Dava türüne göre ilgili kanunlar
        type_laws = {
            'boşanma': ['TMK', 'Aile Mahkemeleri Kanunu'],
            'alacak': ['TBK', 'İİK', 'HUMK'],
            'iş': ['İK', 'Sosyal Güvenlik Kanunu'],
            'miras': ['TMK', 'Veraset ve İntikal Vergisi Kanunu'],
            'ceza': ['TCK', 'CMK'],
            'ticaret': ['TTK', 'TBK'],
            'tapu': ['TMK', 'Tapu Kanunu'],
            'trafik': ['Karayolları Trafik Kanunu', 'TBK'],
            'idari': ['İdari Yargılama Usulü Kanunu', 'İYUK']
        }
        
        laws = type_laws.get(case_type, ['TBK', 'HUMK'])
        
        for law in laws:
            relevant_laws.append({
                'name': law,
                'relevance': 'Yüksek',
                'description': f'{case_type.title()} davaları için temel kanun'
            })
        
        return relevant_laws

    def _load_faiss_index(self, alan_adi):
        """FAISS indeksini lazy loading ile yükle"""
        if alan_adi in self._loaded_indexes:
            return self._loaded_indexes[alan_adi]
        
        index_path = os.path.join(self.faiss_dir, f"faiss_{alan_adi}.index")
        map_path = os.path.join(self.faiss_dir, f"mapping_{alan_adi}.pkl")
        
        try:
            if os.path.exists(index_path) and os.path.exists(map_path):
                index = faiss.read_index(index_path)
                with open(map_path, "rb") as f:
                    mapping = pickle.load(f)
                
                self._loaded_indexes[alan_adi] = {"index": index, "mapping": mapping}
                return self._loaded_indexes[alan_adi]
        except Exception as e:
            logger.error(f"FAISS index loading error for {alan_adi}: {str(e)}")
        return None
    
    def _calculate_case_relevance(self, case_text, karar_data, legal_keywords):
        """Dava dosyası için alakalılık skorunu hesapla"""
        karar_text = f"{karar_data.get('ozet', '')} {karar_data.get('metin', '')}".lower()
        case_lower = case_text.lower()
        
        # Anahtar kelime eşleşme skoru
        keyword_score = 0
        for keyword in legal_keywords:
            if keyword.lower() in karar_text:
                keyword_score += 5
        
        # Hukuki kavram eşleşme skoru
        concept_score = 0
        for concept in self.legal_concepts.keys():
            if concept in case_lower and concept in karar_text:
                concept_score += 8
        
        # Dava türü eşleşme skoru
        case_type_score = 0
        for case_type, patterns in self.case_types.items():
            case_matches = sum(1 for pattern in patterns if re.search(pattern, case_lower, re.IGNORECASE))
            karar_matches = sum(1 for pattern in patterns if re.search(pattern, karar_text, re.IGNORECASE))
            if case_matches > 0 and karar_matches > 0:
                case_type_score += 10
        
        # Toplam skor
        total_score = min(keyword_score + concept_score + case_type_score, 100)
        return total_score
    
    def _find_similar_cases(self, case_type_info, legal_issues, case_text=""):
        """FAISS ile benzer davaları bul - Maksimum 20 karar"""
        similar_cases = []
        
        try:
            # Hukuki anahtar kelimeleri çıkar
            legal_keywords = []
            for issue in legal_issues:
                legal_keywords.append(issue['concept'])
            
            # Dava türü anahtar kelimelerini ekle
            case_type = case_type_info['type']
            if case_type in self.case_types:
                legal_keywords.extend([pattern.replace(r'\b', '').replace(r'\s*', ' ') for pattern in self.case_types[case_type][:3]])
            
            # Embedding oluştur
            query_text = f"{case_text} {' '.join(legal_keywords)}"
            embedding = self.embedding_model.encode([query_text])
            
            # FAISS dizinlerini tara
            top_results = []
            available_indexes = [f.replace('faiss_', '').replace('.index', '') for f in os.listdir(self.faiss_dir) if f.endswith('.index')]
            
            for alan_adi in available_indexes:
                data = self._load_faiss_index(alan_adi)
                if data is None:
                    continue
                
                index = data["index"]
                mapping = data["mapping"]
                
                # Arama yap
                D, I = index.search(np.array(embedding).astype('float32'), 10)
                
                for dist, idx in zip(D[0], I[0]):
                    if idx != -1 and idx < len(mapping):
                        karar_data = mapping[idx]
                        
                        # Alakalılık skorunu hesapla
                        relevance_score = self._calculate_case_relevance(case_text, karar_data, legal_keywords)
                        
                        if relevance_score >= 30:  # Minimum alakalılık eşiği
                            combined_score = (1.0 - dist) * 0.3 + (relevance_score / 100) * 0.7
                            top_results.append((combined_score, karar_data, alan_adi, relevance_score))
            
            # Skorlara göre sırala ve en iyi 20'yi al
            sorted_results = sorted(top_results, key=lambda x: x[0], reverse=True)[:20]
            
            for combined_score, karar_data, alan_adi, relevance_score in sorted_results:
                similar_cases.append({
                    'title': karar_data.get('ozet', 'Karar özeti mevcut değil')[:100],
                    'court': karar_data.get('mahkeme', 'Bilinmeyen Mahkeme'),
                    'decision_date': karar_data.get('tarih', 'Tarih belirtilmemiş'),
                    'case_number': karar_data.get('esas_no', 'Esas numarası belirtilmemiş'),
                    'decision_number': karar_data.get('karar_no', 'Karar numarası belirtilmemiş'),
                    'relevance_score': relevance_score,
                    'similarity': f"{int(combined_score * 100)}%",
                    'legal_area': alan_adi.replace('_', ' ').title(),
                    'summary': karar_data.get('ozet', 'Özet mevcut değil')[:200]
                })
                
        except Exception as e:
            logger.error(f"Similar cases search error: {str(e)}")
        
        return similar_cases

    def _generate_recommendations(self, case_type_info, missing_docs, legal_issues, case_text=""):
        """Detaylı hukuki strateji önerileri oluştur"""
        recommendations = []
        case_type = case_type_info['type']
        
        # 1. Eksik belgeler için detaylı öneriler
        if missing_docs['missing']:
            critical_missing = [doc for doc in missing_docs['missing'] if doc['importance'] == 'Kritik']
            high_missing = [doc for doc in missing_docs['missing'] if doc['importance'] == 'Yüksek']
            
            if critical_missing:
                recommendations.append({
                    'type': 'Kritik Eksik Belgeler',
                    'priority': 'Acil',
                    'action': f"{len(critical_missing)} kritik belge eksik. Bu belgeler olmadan dava risklidir.",
                    'details': [f"• {doc['document']}: {doc['reason']}" for doc in critical_missing],
                    'timeline': 'Derhal temin edilmeli'
                })
            
            if high_missing:
                recommendations.append({
                    'type': 'Önemli Eksik Belgeler',
                    'priority': 'Yüksek',
                    'action': f"{len(high_missing)} önemli belge eksik. Dava başarısı için önerilir.",
                    'details': [f"• {doc['document']}: {doc['reason']}" for doc in high_missing],
                    'timeline': '1-2 hafta içinde temin edilmeli'
                })
        
        # 2. Dava türüne özel detaylı stratejiler
        detailed_strategies = {
            'boşanma': [
                {
                    'type': 'Boşanma Sebepleri Stratejisi',
                    'priority': 'Yüksek',
                    'action': 'Boşanma sebeplerini TMK 166. madde kapsamında belgelendirin',
                    'details': [
                        '• Evlilik birliği temelinden sarsılmışsa somut olayları belgeleyin',
                        '• Zina iddiası varsa kesin delillerle destekleyin',
                        '• Şiddet durumunda adli tıp raporu ve tanık beyanları alın',
                        '• Anlaşmalı boşanma için karşı tarafın rızasını yazılı olarak alın'
                    ],
                    'timeline': 'Dava süresince'
                },
                {
                    'type': 'Nafaka Stratejisi',
                    'priority': 'Yüksek',
                    'action': 'Nafaka hesaplamasını detaylandırın',
                    'details': [
                        '• Her iki tarafın gelir durumunu belgeleyin',
                        '• Çocuğun ihtiyaçlarını detaylı listeleyin',
                        '• Yaşam standardını koruyan nafaka miktarını hesaplayın',
                        '• Geçici nafaka talebini değerlendirin'
                    ],
                    'timeline': 'Dilekçe aşamasından itibaren'
                }
            ],
            'alacak': [
                {
                    'type': 'Alacak İspatı Stratejisi',
                    'priority': 'Kritik',
                    'action': 'Alacağın varlığını hukuki ve fiili yönlerden ispatlayın',
                    'details': [
                        '• Yazılı senet varsa aslını mahkemeye sunun',
                        '• Sözlü borçlarda tanık beyanları ve ikrar alın',
                        '• Mal/hizmet teslimi belgelerini hazırlayın',
                        '• Ödeme planı ve vade şartlarını netleştirin'
                    ],
                    'timeline': 'İddia aşamasında'
                },
                {
                    'type': 'Zamanaşımı Stratejisi',
                    'priority': 'Acil',
                    'action': 'Zamanaşımı sürelerini kontrol edin ve durdurun',
                    'details': [
                        '• Genel alacaklarda 10 yıllık zamanaşımı süresi',
                        '• Ticari alacaklarda 5 yıllık süre',
                        '• Zamanaşımını kesen olayları belgeleyin',
                        '• Gerekirse ihtiyati haciz talebinde bulunun'
                    ],
                    'timeline': 'Derhal'
                }
            ],
            'iş': [
                {
                    'type': 'İş Sözleşmesi Analizi',
                    'priority': 'Yüksek',
                    'action': 'İş sözleşmesi şartlarını detaylı analiz edin',
                    'details': [
                        '• Sözleşmede belirsiz süreli/belirli süreli durumu',
                        '• Fesih koşulları ve ihbar süreleri',
                        '• Maaş, prim ve yan haklar',
                        '• Rekabet yasağı ve gizlilik şartları'
                    ],
                    'timeline': 'Dava öncesi'
                },
                {
                    'type': 'İşten Çıkarma Gerekçeleri',
                    'priority': 'Kritik',
                    'action': 'İşten çıkarma gerekçelerinin hukuka uygunluğunu inceleyin',
                    'details': [
                        '• Haklı nedenle fesih şartlarını kontrol edin',
                        '• Disiplin sürecinin usulüne uygunluğunu araştırın',
                        '• Savunma hakkı verilip verilmediğini kontrol edin',
                        '• Eşit davranma ilkesine aykırılık olup olmadığını değerlendirin'
                    ],
                    'timeline': 'Dava başlangıcı'
                }
            ],
            'miras': [
                {
                    'type': 'Mirasçılık Sıfatı',
                    'priority': 'Kritik',
                    'action': 'Mirasçılık sıfatınızı kesin olarak belgeleyin',
                    'details': [
                        '• Nüfus kayıtları ile aile bağını ispatlayın',
                        '• Veraset ilamı alın veya mevcut olanı güncelleyin',
                        '• Diğer mirasçıları tespit edin',
                        '• Mirastan feragat durumlarını araştırın'
                    ],
                    'timeline': 'Dava öncesi'
                },
                {
                    'type': 'Miras Payı Hesaplama',
                    'priority': 'Yüksek',
                    'action': 'Miras payınızı hukuki kurallara göre hesaplayın',
                    'details': [
                        '• Saklı pay kurallarını uygulayın',
                        '• Vasiyetin varlığını ve geçerliliğini kontrol edin',
                        '• Miras bırakanın borçlarını tespit edin',
                        '• Mal varlığının değerini ekspertiz ile belirleyin'
                    ],
                    'timeline': 'Analiz aşamasında'
                }
            ]
        }
        
        # Dava türüne özel stratejileri ekle
        if case_type in detailed_strategies:
            recommendations.extend(detailed_strategies[case_type])
        
        # 3. Hukuki konular için özel öneriler
        for issue in legal_issues:
            if issue['concept'] == 'zamanaşımı':
                recommendations.append({
                    'type': 'Zamanaşımı Acil Uyarısı',
                    'priority': 'Acil',
                    'action': 'Zamanaşımı süresi dolmak üzere - Derhal harekete geçin',
                    'details': [
                        '• Hak kaybını önlemek için ivedilik gerekiyor',
                        '• Zamanaşımını kesen olayları belgeleyin',
                        '• Gerekirse ihtiyati tedbir talep edin',
                        '• Dava açma süresini kaçırmayın'
                    ],
                    'timeline': 'Derhal'
                })
            elif issue['concept'] == 'delil':
                recommendations.append({
                    'type': 'Delil Hukuki Değerlendirmesi',
                    'priority': 'Yüksek',
                    'action': 'Delillerin hukuki açıdan değerlendirilmesi',
                    'details': [
                        '• HMK m.187 vd. kapsamında delil hukuku kuralları',
                        '• İspat yükü ve ispat standardı analizi',
                        '• Kesin delil ve takdiri delil ayrımı',
                        '• Delillerin kabul edilebilirlik şartları'
                    ],
                    'timeline': 'Hukuki inceleme aşamasında'
                })
        
        
        return recommendations