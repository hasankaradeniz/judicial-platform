# core/ai_legal_assistant.py

import re
import logging
from django.core.cache import cache
from .models import Legislation, JudicialDecision
import google.generativeai as genai
from django.conf import settings

logger = logging.getLogger(__name__)

class AILegalAssistant:
    """AI Hukuki Asistan - Doğal dille hukuki sorular yanıtlama"""
    
    def __init__(self):
        # Gemini API'yi yapılandır
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.gemini_model = genai.GenerativeModel(model_name="gemini-3-pro-preview")
        
        self.legal_keywords = {
            'miras': ['miras', 'veraset', 'muris', 'mirasçı', 'tereeke'],
            'boşanma': ['boşanma', 'talak', 'ayrılık', 'nafaka', 'velayet'],
            'sözleşme': ['sözleşme', 'mukavele', 'kontrat', 'anlaşma'],
            'ceza': ['ceza', 'suç', 'mahkumiyet', 'hapis', 'para cezası'],
            'iş': ['işçi', 'işveren', 'iş sözleşmesi', 'kıdem tazminatı', 'işten çıkarma'],
            'ticaret': ['ticaret', 'şirket', 'ortaklık', 'sermaye', 'ticari'],
            'tapu': ['tapu', 'mülkiyet', 'gayrimenkul', 'satış', 'devir'],
            'vergi': ['vergi', 'vergiler', 'beyan', 'ödeme', 'gecikme faizi'],
            'icra': ['icra', 'haciz', 'borç', 'alacak', 'ihtiyati tedbir']
        }
        
        self.law_codes = {
            'TMK': {'name': 'Türk Medeni Kanunu', 'number': '4721'},
            'TCK': {'name': 'Türk Ceza Kanunu', 'number': '5237'},
            'TBK': {'name': 'Türk Borçlar Kanunu', 'number': '6098'},
            'TTK': {'name': 'Türk Ticaret Kanunu', 'number': '6102'},
            'İİK': {'name': 'İcra İflas Kanunu', 'number': '2004'},
            'İK': {'name': 'İş Kanunu', 'number': '4857'},
            'VUK': {'name': 'Vergi Usul Kanunu', 'number': '213'},
            'HUMK': {'name': 'Hukuk Muhakemeleri Kanunu', 'number': '6100'},
            'CMK': {'name': 'Ceza Muhakemeleri Kanunu', 'number': '5271'}
        }

    def process_question(self, question, user=None):
        """Doğal dille gelen soruyu işle ve yanıtla"""
        try:
            # Cache kontrolü
            cache_key = f"ai_question_{hash(question)}"
            cached_result = cache.get(cache_key)
            if cached_result:
                return cached_result

            # Soruyu temizle ve analiz et
            cleaned_question = self._clean_question(question)
            legal_area = self._identify_legal_area(cleaned_question)
            law_references = self._extract_law_references(cleaned_question)
            
            # Relevant mevzuat ara
            search_terms = self._extract_search_terms(cleaned_question, legal_area)
            relevant_laws = self._search_relevant_legislation(search_terms)
            
            # AI yanıtı oluştur
            response = self._generate_ai_response(
                question=cleaned_question,
                legal_area=legal_area,
                law_references=law_references,
                relevant_laws=relevant_laws
            )
            
            # Cache'e kaydet
            cache.set(cache_key, response, 3600)  # 1 saat
            
            return response
            
        except Exception as e:
            logger.error(f"AI Legal Assistant error: {str(e)}")
            return {
                'success': False,
                'error': 'Üzgünüm, şu anda sorunuzu yanıtlayamıyorum. Lütfen daha sonra tekrar deneyin.',
                'suggestions': [
                    'Sorunuzu daha basit ifadelerle tekrar sormayı deneyin',
                    'Belirli bir kanun maddesi hakkında soru sorun',
                    'Arama kutusunu kullanarak manuel arama yapın'
                ]
            }

    def _clean_question(self, question):
        """Soruyu temizle ve normalize et"""
        # Türkçe karakterleri düzelt
        question = question.strip().lower()
        
        # Gereksiz kelimeleri temizle
        stop_words = ['nedir', 'ne', 'nasıl', 'ne kadar', 'hakkında', 'ile ilgili', 'için']
        words = question.split()
        cleaned_words = [word for word in words if word not in stop_words]
        
        return ' '.join(cleaned_words)

    def _identify_legal_area(self, question):
        """Sorunun hangi hukuk alanıyla ilgili olduğunu tespit et"""
        max_score = 0
        identified_area = 'genel'
        
        for area, keywords in self.legal_keywords.items():
            score = sum(1 for keyword in keywords if keyword in question)
            if score > max_score:
                max_score = score
                identified_area = area
        
        return identified_area if max_score > 0 else 'genel'

    def _extract_law_references(self, question):
        """Soruda geçen kanun referanslarını çıkar"""
        references = []
        
        for code, info in self.law_codes.items():
            if code.lower() in question or info['name'].lower() in question:
                references.append({
                    'code': code,
                    'name': info['name'],
                    'number': info['number']
                })
        
        # Madde numaralarını ara
        article_pattern = r'(\d+)\s*\.?\s*madde'
        articles = re.findall(article_pattern, question)
        
        return {
            'law_codes': references,
            'articles': articles
        }

    def _extract_search_terms(self, question, legal_area):
        """Arama terimlerini çıkar"""
        terms = []
        
        # Hukuk alanına göre terimler ekle
        if legal_area in self.legal_keywords:
            terms.extend(self.legal_keywords[legal_area])
        
        # Soruda geçen önemli terimleri ekle
        important_words = []
        words = question.split()
        for word in words:
            if len(word) > 3 and word not in ['hakkında', 'nedir', 'nasıl']:
                important_words.append(word)
        
        terms.extend(important_words)
        return list(set(terms))  # Tekrarları kaldır

    def _search_relevant_legislation(self, search_terms):
        """İlgili mevzuatı ara"""
        relevant_laws = []
        
        try:
            # İlk terimi kullanarak arama yap
            if search_terms:
                search_query = search_terms[0]
                
                # External mevzuat search would be here
                # Currently disabled to avoid import errors
                pass
                
                # Dahili mevzuat ara
                internal_results = Legislation.objects.filter(
                    baslik__icontains=search_query
                )[:2]
                
                for result in internal_results:
                    relevant_laws.append({
                        'title': result.baslik,
                        'type': 'Kanun',
                        'summary': result.tam_metin[:200] + '...' if result.tam_metin else '',
                        'url': f'/legislation/{result.id}/',
                        'source': 'internal'
                    })
                    
        except Exception as e:
            logger.error(f"Search error in AI assistant: {str(e)}")
        
        return relevant_laws

    def _generate_ai_response(self, question, legal_area, law_references, relevant_laws):
        """Gemini AI ile hukuki yanıt oluştur"""
        
        try:
            # Gemini için prompt oluştur
            prompt = self._build_legal_prompt(question, legal_area, law_references, relevant_laws)
            
            # Gemini'den yanıt al
            response = self.gemini_model.generate_content(prompt)
            
            if response.text:
                # Yanıtı işle ve yapılandır
                ai_answer = self._format_ai_response(response.text.strip())
                
                return {
                    'success': True,
                    'answer': ai_answer,
                    'legal_area': legal_area,
                    'law_references': law_references,
                    'relevant_laws': relevant_laws
                }
            else:
                # Fallback yanıt
                return self._generate_fallback_response(legal_area, law_references, relevant_laws)
                
        except Exception as e:
            logger.error(f"Gemini AI error: {str(e)}")
            # Hata durumunda fallback yanıt
            return self._generate_fallback_response(legal_area, law_references, relevant_laws)

    def _build_legal_prompt(self, question, legal_area, law_references, relevant_laws):
        """Gemini için hukuki prompt oluştur"""
        
        prompt_parts = [
            "Sen bir Türk hukuku uzmanısın. Aşağıdaki soruyu Türk hukuk sistemine göre yanıtla:",
            f"\nSoru: {question}",
            f"\nTespit edilen hukuk alanı: {legal_area}",
        ]
        
        # Kanun referansları ekle
        if law_references['law_codes']:
            law_names = [ref['name'] for ref in law_references['law_codes']]
            prompt_parts.append(f"\nİlgili kanunlar: {', '.join(law_names)}")
        
        if law_references['articles']:
            articles = ', '.join(law_references['articles'])
            prompt_parts.append(f"\nİlgili maddeler: {articles}")
        
        # İlgili mevzuat bilgisi ekle
        if relevant_laws:
            prompt_parts.append("\nİlgili mevzuat:")
            for law in relevant_laws[:3]:
                prompt_parts.append(f"- {law['title']}")
                if law.get('summary'):
                    prompt_parts.append(f"  Özet: {law['summary']}")
        
        prompt_parts.extend([
            "\nYanıtın aşağıdaki kriterlere uygun olsun:",
            "- Türkçe ve anlaşılır olsun",
            "- Hukuki açıklamalar doğru ve güncel olsun", 
            "- Pratik öneriler içersin",
            "- Yaklaşık 250-350 kelime olsun",
            "- Ana başlığı ### ile başlat (örn: ### Miras Hukuku Açıklaması)",
            "- Her paragraf arasında boş satır bırak",
            "- Paragraflar halinde düzenle",
            "- Önemli noktaları vurgula",
            "- Gerekirse ilgili kanun maddelerine atıf yap",
            "- Son olarak 'Kesin hukuki görüş için avukata danışmanızı öneririm' uyarısını ekle"
        ])
        
        return '\n'.join(prompt_parts)

    def _format_ai_response(self, response_text):
        """AI yanıtını düzenle ve formatla"""
        
        # Gereksiz boşlukları temizle
        formatted = response_text.strip()
        
        # Çok uzun paragrafları böl
        paragraphs = formatted.split('\n\n')
        processed_paragraphs = []
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if len(paragraph) > 500:
                # Uzun paragrafları cümle sonlarında böl
                sentences = paragraph.split('. ')
                current_chunk = ""
                
                for sentence in sentences:
                    if len(current_chunk + sentence) < 300:
                        current_chunk += sentence + ". "
                    else:
                        if current_chunk:
                            processed_paragraphs.append(current_chunk.strip())
                        current_chunk = sentence + ". "
                
                if current_chunk:
                    processed_paragraphs.append(current_chunk.strip())
            else:
                processed_paragraphs.append(paragraph)
        
        return '\n\n'.join(processed_paragraphs)


    def _generate_fallback_response(self, legal_area, law_references, relevant_laws):
        """AI yanıt alınamadığında fallback yanıt"""
        
        # Basit kural tabanlı yanıt
        response_parts = []
        
        if law_references['law_codes']:
            law_names = [ref['name'] for ref in law_references['law_codes']]
            response_parts.append(f"Sorunuz {', '.join(law_names)} kapsamında değerlendirilebilir.")
        
        # Hukuk alanına göre genel bilgi
        area_info = {
            'miras': 'Miras hukuku, kişinin ölümü halinde mal varlığının mirasçılara geçişini düzenler.',
            'boşanma': 'Boşanma davalarında nafaka, mal rejimi ve velayet konuları önemlidir.',
            'sözleşme': 'Sözleşme hukuku, taraflar arasındaki anlaşmaların hukuki sonuçlarını belirler.',
            'ceza': 'Ceza hukuku, suç teşkil eden fiiller ve bunların yaptırımlarını düzenler.',
            'iş': 'İş hukuku, işçi ve işveren arasındaki ilişkileri düzenler.',
            'ticaret': 'Ticaret hukuku, ticari faaliyetler ve şirketler hukukunu kapsar.',
            'tapu': 'Tapu ve mülkiyet hukuku, gayrimenkul haklarını düzenler.',
            'vergi': 'Vergi hukuku, vergi mükellefiyeti ve vergilendirme esaslarını belirler.',
            'icra': 'İcra hukuku, borçların zorla tahsili süreçlerini düzenler.'
        }
        
        if legal_area in area_info:
            response_parts.append(area_info[legal_area])
        
        if relevant_laws:
            response_parts.append("İlgili mevzuat:")
            for law in relevant_laws[:2]:
                response_parts.append(f"• {law['title']}")
        
        if not response_parts:
            response_parts = [
                "Sorunuzla ilgili genel bilgi için ilgili mevzuatı incelemenizi öneririm.",
                "Kesin hukuki görüş için avukata danışmanızı öneririm."
            ]
        
        return {
            'success': True,
            'answer': ' '.join(response_parts),
            'legal_area': legal_area,
            'law_references': law_references,
            'relevant_laws': relevant_laws
        }

    def get_quick_suggestions(self):
        """Hızlı soru önerileri"""
        return [
            "TMK'da miras payları nasıl hesaplanır?",
            "Boşanma davası için gerekli belgeler nelerdir?",
            "İş sözleşmesi feshi için hangi şartlar gerekir?",
            "Ticaret şirketi kurma prosedürü nedir?",
            "Gayrimenkul satışında vergiler kimde?",
            "İcra takibine itiraz nasıl yapılır?",
            "Ceza davalarında zamanaşımı ne kadar?",
            "Sözleşme iptali için gerekçeler nelerdir?"
        ]