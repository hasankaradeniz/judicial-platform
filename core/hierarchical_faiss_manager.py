#!/usr/bin/env python3
"""
Fixed Hierarchical FAISS Manager
Hierarchical FAISS mapping yapısına uygun düzeltilmiş versiyonn
"""
import os
import pickle
import faiss
import numpy as np
from typing import List, Dict, Optional, Tuple
from sentence_transformers import SentenceTransformer

class FixedHierarchicalFAISSManager:
    def __init__(self, faiss_dir: str = "/var/www/judicial_platform/faiss_dizinleri"):
        self.faiss_dir = faiss_dir
        self.model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
        self._loaded_indexes = {}
        
        # Ana kategoriler
        self.main_categories = [
            'oh_medeni_hukuk', 'oh_ticaret_hukuku', 'oh_is_hukuku', 
            'oh_icra_ve_iflas_hukuku', 'oh_fikri_mulkiyet_hukuku',
            'kh_idare_hukuku', 'kh_anayasa_hukuku', 'kh_ceza_hukuku',
            'kh_ceza_muhakemesi_hukuku', 'kh_vergi_hukuku'
        ]

    def load_index(self, category_name: str) -> Optional[Dict]:
        """FAISS index ve mapping dosyasını yükle"""
        if category_name in self._loaded_indexes:
            return self._loaded_indexes[category_name]
        
        index_path = os.path.join(self.faiss_dir, f"faiss_{category_name}.index")
        mapping_path = os.path.join(self.faiss_dir, f"mapping_{category_name}.pkl")
        
        if not os.path.exists(index_path) or not os.path.exists(mapping_path):
            return None
        
        try:
            index = faiss.read_index(index_path)
            with open(mapping_path, "rb") as f:
                mapping_data = pickle.load(f)
            
            # Yeni hierarchical format - mapping_data bir dict
            if isinstance(mapping_data, dict):
                # 'metadata' anahtarında gerçek mapping listesi var
                if 'metadata' in mapping_data:
                    actual_mapping = mapping_data['metadata']
                else:
                    # Fallback - diğer yapıları dene
                    actual_mapping = mapping_data
            else:
                # Eski format - direkt liste
                actual_mapping = mapping_data
            
            self._loaded_indexes[category_name] = {
                'index': index, 
                'mapping': actual_mapping,
                'category': category_name,
                'raw_data': mapping_data  # Debug için
            }
            return self._loaded_indexes[category_name]
        except Exception as e:
            print(f"Error loading {category_name}: {e}")
            return None

    def detect_legal_area(self, query: str) -> List[str]:
        """Sorgudan hukuk alanlarını tespit et"""
        query_lower = query.lower()
        detected_areas = []
        
        # Miras hukuku keywords
        miras_keywords = [
            'miras', 'mirasçı', 'vasiyet', 'tereke', 'saklı pay', 'terekenin paylaşımı',
            'mirasbırakma', 'mirasbırakan', 'ölüme bağlı tasarruf', 'veraset', 'intikal',
            'gayrimenkul devri', 'anne', 'baba', 'çocuk', 'varis', 'varislik'
        ]
        
        # İptal keywords
        iptal_keywords = [
            'iptal', 'butlan', 'fesih', 'bozma', 'geçersizlik', 'hükümsüzlük'
        ]
        
        # Priority matching - miras + iptal = miras hukuku
        if any(word in query_lower for word in miras_keywords):
            detected_areas = ['oh_medeni_hukuk_miras_hukuku', 'oh_medeni_hukuk']
        # Genel medeni hukuk
        elif any(word in query_lower for word in ['medeni', 'tmk', 'gayrimenkul', 'devir']):
            detected_areas = ['oh_medeni_hukuk']
        # Default fallback
        else:
            detected_areas = ['oh_medeni_hukuk']
        
        return detected_areas

    def search_hierarchical(self, query: str, k: int = 50) -> List[Dict]:
        """Hierarchical yapıda arama yap"""
        detected_areas = self.detect_legal_area(query)
        all_results = []
        
        # Önce spesifik alt kategorilerde ara
        for area in detected_areas:
            area_data = self.load_index(area)
            if area_data:
                results = self._search_in_area(query, area_data, k)
                for result in results:
                    result['search_area'] = area
                    result['hierarchical_level'] = 'specific' if '_' in area.replace('oh_', '').replace('kh_', '') else 'general'
                all_results.extend(results)
        
        # Sonuçları similarity score'a göre sırala
        all_results.sort(key=lambda x: x['similarity_score'], reverse=True)
        
        # En iyi k sonucu döndür
        return all_results[:k]

    def _search_in_area(self, query: str, area_data: Dict, k: int) -> List[Dict]:
        """Belirli bir alanda arama yap - mapping yapısını debug et"""
        try:
            # Query embedding
            query_embedding = self.model.encode([query])
            query_embedding = query_embedding.astype('float32')
            
            # FAISS arama
            scores, indices = area_data['index'].search(query_embedding, min(k, area_data['index'].ntotal))
            
            results = []
            mapping = area_data['mapping']
            
            # Debug: mapping yapısını kontrol et
            print(f"Debug - Mapping type: {type(mapping)}")
            if isinstance(mapping, dict):
                print(f"Debug - Dict keys: {list(mapping.keys())}")
                
                # 'metadata' key'ini kontrol et
                if 'metadata' in mapping:
                    actual_mapping = mapping['metadata']
                    print(f"Debug - Metadata type: {type(actual_mapping)}, length: {len(actual_mapping) if hasattr(actual_mapping, '__len__') else 'N/A'}")
                    
                    # Metadata'yı kullan
                    for score, idx in zip(scores[0], indices[0]):
                        if idx < len(actual_mapping) and idx != -1:
                            mapping_data = actual_mapping[idx]
                            
                            result = {
                                'decision_id': mapping_data.get('id', mapping_data.get('decision_id', idx)),
                                'similarity_score': float(score),
                                'legal_area': area_data['category'],
                                'mahkeme': mapping_data.get('mahkeme', 'Bilinmeyen'),
                                'tarih': mapping_data.get('tarih', ''),
                                'sayi': mapping_data.get('sayi', ''),
                                'text_snippet': str(mapping_data.get('text', ''))[:300] + '...',
                                'full_text': mapping_data.get('text', '')
                            }
                            results.append(result)
                else:
                    print("Debug - 'metadata' key bulunamadı")
            else:
                print(f"Debug - Mapping liste, length: {len(mapping)}")
                # Direkt liste olarak kullan
                for score, idx in zip(scores[0], indices[0]):
                    if idx < len(mapping) and idx != -1:
                        mapping_data = mapping[idx]
                        
                        result = {
                            'decision_id': mapping_data.get('id', mapping_data.get('decision_id', idx)),
                            'similarity_score': float(score),
                            'legal_area': area_data['category'],
                            'mahkeme': mapping_data.get('mahkeme', 'Bilinmeyen'),
                            'tarih': mapping_data.get('tarih', ''),
                            'sayi': mapping_data.get('sayi', ''),
                            'text_snippet': str(mapping_data.get('text', ''))[:300] + '...',
                            'full_text': mapping_data.get('text', '')
                        }
                        results.append(result)
            
            return results
        except Exception as e:
            print(f"Search error in {area_data['category']}: {e}")
            return []

    def get_available_categories(self) -> List[str]:
        """Mevcut kategorileri listele"""
        categories = []
        for file in os.listdir(self.faiss_dir):
            if file.startswith('faiss_') and file.endswith('.index'):
                category = file.replace('faiss_', '').replace('.index', '')
                categories.append(category)
        return sorted(categories)

# Test fonksiyonu
def test_fixed_hierarchical_search():
    """Fixed hierarchical arama sistemi test et"""
    manager = FixedHierarchicalFAISSManager()
    
    test_query = "Müvekkilin annesi 80 yaşında adına kayıtlı olan tek gayrimenkulkü çocuklarından birinin üzerine devretmiş. Diğer çocuğu bu devir işlemnin iptali için dava açmak istiyor."
    
    print(f"🔍 Test sorgusu: {test_query}")
    print("="*80)
    
    # Alan tespiti
    detected_areas = manager.detect_legal_area(test_query)
    print(f"📍 Tespit edilen alanlar: {detected_areas}")
    
    # Arama
    results = manager.search_hierarchical(test_query, k=10)
    
    print(f"📊 Bulunan sonuç sayısı: {len(results)}")
    print("="*80)
    
    for i, result in enumerate(results[:5], 1):
        print(f"{i}. {result['mahkeme']} - {result['tarih']}")
        print(f"   Similarity: {result['similarity_score']:.4f}")
        print(f"   Alan: {result['legal_area']}")
        print(f"   Snippet: {result['text_snippet'][:150]}...")
        print()

if __name__ == "__main__":
    test_fixed_hierarchical_search()