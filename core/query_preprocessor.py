"""
Türkçe Mevzuat Query Preprocessing
Normal kullanıcı sorgularını API'nin anlayacağı formatına çevirir
"""
import re
from typing import Dict, List, Optional, Tuple

class TurkishLegalQueryPreprocessor:
    """Türkçe hukuki sorguları işler"""
    
    def __init__(self):
        # Yaygın hukuki terimler ve karşılıkları
        self.term_mappings = {
            # Tüketici
            "tüketici": ["tüketici", "korunması", "6502"],
            "tüketici hakları": ["tüketici", "hakları", "korunması"],
            "tüketici koruma": ["tüketici", "korunması"],
            "e-ticaret": ["elektronik", "ticaret", "6563"],
            "online alışveriş": ["elektronik", "ticaret"],
            
            # Medeni Hukuk
            "medeni": ["medeni", "4721"],
            "medeni hukuk": ["medeni", "kanunu"],
            "evlilik": ["medeni", "evlilik", "nikah"],
            "boşanma": ["medeni", "boşanma"],
            "miras": ["medeni", "miras", "veraset"],
            "velayet": ["medeni", "velayet", "çocuk"],
            "vesayet": ["medeni", "vesayet"],
            
            # Borçlar Hukuku
            "borç": ["borçlar", "6098"],
            "sözleşme": ["borçlar", "sözleşme", "akdi"],
            "kira": ["borçlar", "kira", "kiralama"],
            "satış": ["borçlar", "satış", "alım"],
            "hizmet": ["borçlar", "hizmet", "eser"],
            
            # Ticaret Hukuku
            "ticaret": ["ticaret", "6102"],
            "şirket": ["ticaret", "şirket", "ortaklık"],
            "anonim şirket": ["ticaret", "anonim", "şirket"],
            "limited şirket": ["ticaret", "limited", "şirket"],
            "kooperatif": ["ticaret", "kooperatif"],
            
            # İş Hukuku  
            "iş": ["iş", "çalışma", "4857"],
            "işçi": ["iş", "işçi", "çalışan"],
            "işveren": ["iş", "işveren", "çalıştıran"],
            "maaş": ["iş", "maaş", "ücret"],
            "kıdem": ["iş", "kıdem", "tazminat"],
            "işten çıkarma": ["iş", "fesih", "çıkarma"],
            "sendika": ["sendika", "toplu", "sözleşme"],
            
            # Ceza Hukuku
            "ceza": ["ceza", "5237"],
            "suç": ["ceza", "suç", "cürüm"],
            "hırsızlık": ["ceza", "hırsızlık"],
            "dolandırıcılık": ["ceza", "dolandırıcılık"],
            "cinayet": ["ceza", "öldürme", "cinayet"],
            
            # Vergi
            "vergi": ["vergi", "193"],
            "gelir vergisi": ["gelir", "vergi", "193"],
            "kurumlar vergisi": ["kurumlar", "vergi", "5520"],
            "kdv": ["katma", "değer", "vergi", "3065"],
            
            # İcra İflas
            "icra": ["icra", "iflas", "2004"],
            "borç takibi": ["icra", "takip", "borç"],
            "haciz": ["icra", "haciz", "satış"],
            
            # Belediye
            "belediye": ["belediye", "5393"],
            "imar": ["imar", "3194", "belediye"],
            "yapı": ["yapı", "imar", "3194"],
            "ruhsat": ["yapı", "ruhsat", "imar"],
            
            # Sağlık
            "sağlık": ["sağlık", "1219"],
            "hastane": ["sağlık", "hastane"],
            "doktor": ["sağlık", "doktor", "hekim"],
            "ilaç": ["sağlık", "ilaç", "eczane"],
            
            # Fikri Mülkiyet
            "fikri": ["fikir"],
            "fikri mülkiyet": ["fikir", "mülkiyet", "sınai"],
            "patent": ["patent"],
            "marka": ["marka"],
            "telif": ["fikir", "sanat", "eser"],
            "tasarım": ["endüstriyel", "tasarım"],
            
            # Eğitim
            "eğitim": ["eğitim", "1739"],
            "okul": ["eğitim", "okul"],
            "öğretmen": ["eğitim", "öğretmen"],
            "üniversite": ["eğitim", "üniversite", "yüksek"],
        }
        
        # Kanun numaraları ve adları
        self.law_numbers = {
            "4721": "Türk Medeni Kanunu",
            "6098": "Türk Borçlar Kanunu", 
            "6102": "Türk Ticaret Kanunu",
            "5237": "Türk Ceza Kanunu",
            "4857": "İş Kanunu",
            "6502": "Tüketicinin Korunması Hakkında Kanun",
            "6563": "Elektronik Ticaretin Düzenlenmesi Hakkında Kanun",
            "193": "Gelir Vergisi Kanunu",
            "5520": "Kurumlar Vergisi Kanunu",
            "3065": "Katma Değer Vergi Kanunu",
            "2004": "İcra ve İflas Kanunu",
            "5393": "Belediye Kanunu",
            "3194": "İmar Kanunu",
            "1219": "Tababet ve Şuabatı San'atının Tarzı İcrasına Dair Kanun",
            "1739": "Milli Eğitim Temel Kanunu"
        }
        
        # Stop words (yaygın ama anlamsız kelimeler)
        self.stop_words = {
            "hakkında", "dair", "ile", "den", "dan", "nin", "nın", "nun", "nün",
            "de", "da", "te", "ta", "ye", "ya", "re", "ra", "le", "la",
            "i", "u", "ü", "ı", "e", "a", "o", "ö"
        }
    
    def preprocess_query(self, query: str) -> Dict[str, any]:
        """
        Ana preprocessing fonksiyonu
        Kullanıcı sorgusunu API formatına çevirir
        """
        if not query or len(query.strip()) < 2:
            return {"mevzuatAdi": "", "phrase": ""}
        
        original_query = query.strip().lower()
        
        # 1. Sayısal sorgu kontrolü (kanun numarası)
        if self._is_law_number(original_query):
            return self._handle_law_number(original_query)
        
        # 2. Term mapping (akıllı eşleştirme)
        mapped_terms = self._apply_term_mapping(original_query)
        if mapped_terms:
            return self._create_search_payload(mapped_terms, original_query)
        
        # 3. Proximity search (2+ kelime)
        words = original_query.split()
        if len(words) > 1:
            return self._create_proximity_search(words, original_query)
        
        # 4. Tek kelime - basit arama
        return {"mevzuatAdi": original_query.title(), "phrase": ""}
    
    def _is_law_number(self, query: str) -> bool:
        """Sorgu kanun numarası mı kontrol eder"""
        return query.isdigit() and len(query) >= 3
    
    def _handle_law_number(self, query: str) -> Dict[str, any]:
        """Kanun numarası sorgularını işler"""
        law_name = self.law_numbers.get(query, f"{query} sayılı kanun")
        return {
            "mevzuatNo": query,
            "mevzuatAdi": law_name,
            "phrase": ""
        }
    
    def _apply_term_mapping(self, query: str) -> Optional[List[str]]:
        """Term mapping uygular"""
        
        # Exact match
        if query in self.term_mappings:
            return self.term_mappings[query]
        
        # Partial match (query içinde term geçiyor mu)
        for term, mapping in self.term_mappings.items():
            if term in query or query in term:
                return mapping
        
        # Fuzzy match (benzer kelimeler)
        for term, mapping in self.term_mappings.items():
            if self._fuzzy_match(query, term):
                return mapping
        
        return None
    
    def _fuzzy_match(self, query: str, term: str) -> bool:
        """Fuzzy string matching"""
        # Basit Levenshtein distance approximation
        if abs(len(query) - len(term)) > 3:
            return False
        
        # Ortak karakter sayısı
        common_chars = len(set(query) & set(term))
        return common_chars >= min(len(query), len(term)) - 2
    
    def _create_search_payload(self, mapped_terms: List[str], original: str) -> Dict[str, any]:
        """Mapped terms'den search payload oluşturur"""
        
        # Kanun numarası varsa öncelik ver
        law_number = None
        for term in mapped_terms:
            if term.isdigit() and len(term) >= 3:
                law_number = term
                break
        
        if law_number:
            return self._handle_law_number(law_number)
        
        # Phrase search oluştur
        filtered_terms = [t for t in mapped_terms if t not in self.stop_words and len(t) > 1]
        
        if len(filtered_terms) == 1:
            return {"mevzuatAdi": filtered_terms[0].title(), "phrase": ""}
        elif len(filtered_terms) > 1:
            # Simple phrase search - API kendisi AND logic uygular
            phrase = " ".join(filtered_terms)
            return {"phrase": phrase, "mevzuatAdi": ""}
        else:
            return {"mevzuatAdi": original.title(), "phrase": ""}
    
    def _create_proximity_search(self, words: List[str], original: str) -> Dict[str, any]:
        """Proximity search oluşturur"""
        
        # Stop words'leri filtrele
        filtered_words = [w for w in words if w not in self.stop_words and len(w) > 2]
        
        if len(filtered_words) >= 2:
            # Proximity search: "word1 word2"~5
            phrase = f'"{" ".join(filtered_words)}"~5'
            return {"phrase": phrase, "mevzuatAdi": ""}
        elif len(filtered_words) == 1:
            return {"mevzuatAdi": filtered_words[0].title(), "phrase": ""}
        else:
            return {"mevzuatAdi": original.title(), "phrase": ""}
    
    def get_suggestions(self, query: str) -> List[str]:
        """Kullanıcıya arama önerileri verir"""
        query = query.lower().strip()
        suggestions = []
        
        # Term mapping'den benzer terimler
        for term in self.term_mappings.keys():
            if query in term or term in query:
                suggestions.append(term)
        
        # Kanun adları
        for number, name in self.law_numbers.items():
            if query in name.lower() or query in number:
                suggestions.append(f"{name} ({number})")
        
        return suggestions[:5]  # En fazla 5 öneri


# Global instance
query_processor = TurkishLegalQueryPreprocessor()


def preprocess_user_query(query: str) -> Dict[str, any]:
    """Kolay kullanım için wrapper fonksiyon"""
    return query_processor.preprocess_query(query)


def get_query_suggestions(query: str) -> List[str]:
    """Arama önerileri wrapper fonksiyonu"""
    return query_processor.get_suggestions(query)