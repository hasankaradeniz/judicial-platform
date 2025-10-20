import os
import pickle
import faiss
import numpy as np
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
import logging
from django.conf import settings
from .legal_area_detector import LegalAreaDetector

logger = logging.getLogger(__name__)

class HybridFAISSSearch:
    def __init__(self):
        self.base_path = '/var/www/judicial_platform/faiss_dizinleri'
        self.detector = LegalAreaDetector()
        self.embedding_model = None
        self.loaded_indexes = {}
        
    def _get_embedding_model(self):
        if self.embedding_model is None:
            try:
                self.embedding_model = SentenceTransformer(
                    'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
                )
            except Exception as e:
                logger.error(f"Model load error: {e}")
                return None
        return self.embedding_model
    
    def _load_area_index(self, area_name: str) -> Optional[Dict]:
        if area_name in self.loaded_indexes:
            return self.loaded_indexes[area_name]
        
        index_file = os.path.join(self.base_path, f'faiss_{area_name}.index')
        mapping_file = os.path.join(self.base_path, f'mapping_{area_name}.pkl')
        
        if not os.path.exists(index_file) or not os.path.exists(mapping_file):
            return None
        
        try:
            faiss_index = faiss.read_index(index_file)
            
            with open(mapping_file, 'rb') as f:
                mapping = pickle.load(f)
            
            area_data = {
                'index': faiss_index,
                'mapping': mapping,
                'loaded_at': os.path.getmtime(index_file)
            }
            
            self.loaded_indexes[area_name] = area_data
            return area_data
            
        except Exception as e:
            logger.error(f"Error loading {area_name}: {e}")
            return None
    
    def search_in_area(self, query: str, area_name: str, k: int = 25) -> List[Dict]:
        area_data = self._load_area_index(area_name)
        if not area_data:
            return []
        
        model = self._get_embedding_model()
        if not model:
            return []
        
        try:
            query_embedding = model.encode([query])
            query_embedding = query_embedding.astype('float32')
            
            scores, indices = area_data['index'].search(query_embedding, min(k, len(area_data['mapping'])))
            
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx < len(area_data['mapping']) and idx != -1:
                    mapping_data = area_data['mapping'][idx]
                    results.append({
                        'decision_id': mapping_data.get('id', mapping_data.get('decision_id')),
                        'similarity_score': float(score),
                        'legal_area': area_name,
                        'mahkeme': mapping_data.get('mahkeme', ''),
                        'text_snippet': str(mapping_data.get('text', ''))[:200] + '...'
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"Search error in {area_name}: {e}")
            return []
    
    def smart_search(self, query: str, k: int = 25) -> Dict:
        detected_areas = self.detector.get_multiple_areas(query, threshold=0.05)
        primary_area = self.detector.get_primary_area(query)
        
        results = {
            'primary_area': primary_area,
            'detected_areas': detected_areas,
            'results': [],
            'search_stats': {}
        }
        
        primary_results = self.search_in_area(query, primary_area, k)
        results['results'].extend(primary_results)
        results['search_stats'][primary_area] = len(primary_results)
        
        if len(primary_results) < k // 2 and len(detected_areas) > 1:
            remaining_k = k - len(primary_results)
            per_area_k = max(5, remaining_k // (len(detected_areas) - 1))
            
            for area in detected_areas[1:4]:
                if area != primary_area and area in self.detector.available_areas:
                    area_results = self.search_in_area(query, area, per_area_k)
                    results['results'].extend(area_results)
                    results['search_stats'][area] = len(area_results)
        
        results['results'] = sorted(results['results'], 
                                  key=lambda x: x['similarity_score'], 
                                  reverse=True)
        
        results['results'] = results['results'][:k]
        results['total_found'] = len(results['results'])
        
        return results
