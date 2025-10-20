import os
import pickle
import faiss
import numpy as np
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
import logging
from django.conf import settings
from .legal_area_detector import LegalAreaDetector
from .models import JudicialDecision

logger = logging.getLogger(__name__)

class AdvancedHybridSearch:
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
        
    def _load_legacy_index(self, area_name: str) -> Optional[Dict]:
        """Legacy index'i yükle (eski sistem)"""
        if f'legacy_{area_name}' in self.loaded_indexes:
            return self.loaded_indexes[f'legacy_{area_name}']
        
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
                'type': 'legacy',
                'loaded_at': os.path.getmtime(index_file)
            }
            
            self.loaded_indexes[f'legacy_{area_name}'] = area_data
            return area_data
            
        except Exception as e:
            logger.error(f"Error loading legacy index {area_name}: {e}")
            return None
    
    def _search_database_decisions(self, query: str, legal_area: str, k: int = 25) -> List[Dict]:
        """Veritabanından doğrudan arama yap"""
        try:
            # İlgili alandaki kararları getir
            decisions = JudicialDecision.objects.filter(
                detected_legal_area=legal_area
            ).exclude(
                karar_tam_metni__isnull=True
            ).exclude(
                karar_tam_metni__exact=''
            )[:k * 2]  # Fazladan getir, embedding ile filtreleyeceğiz
            
            if not decisions:
                return []
            
            model = self._get_embedding_model()
            if not model:
                return []
            
            # Query embedding
            query_embedding = model.encode([query])
            query_embedding = query_embedding.astype('float32')
            
            # Decision embeddings
            texts = []
            decision_data = []
            for decision in decisions:
                text = (decision.karar_ozeti or '') + ' ' + (decision.karar_tam_metni or '')
                texts.append(text)
                decision_data.append(decision)
            
            if not texts:
                return []
            
            # Batch embedding
            decision_embeddings = model.encode(texts)
            decision_embeddings = decision_embeddings.astype('float32')
            
            # Cosine similarity hesapla
            query_norm = np.linalg.norm(query_embedding)
            decision_norms = np.linalg.norm(decision_embeddings, axis=1)
            
            similarities = np.dot(decision_embeddings, query_embedding.T).flatten()
            similarities = similarities / (decision_norms * query_norm)
            
            # En yüksek skorlu k sonucu al
            top_indices = np.argsort(similarities)[::-1][:k]
            
            results = []
            for idx in top_indices:
                if similarities[idx] > 0.1:  # Minimum threshold
                    decision = decision_data[idx]
                    results.append({
                        'decision_id': decision.id,
                        'similarity_score': float(similarities[idx]),
                        'legal_area': legal_area,
                        'mahkeme': decision.karar_veren_mahkeme or '',
                        'text_snippet': texts[idx][:200] + '...',
                        'type': 'database',
                        'karar_tarihi': str(decision.karar_tarihi) if decision.karar_tarihi else ''
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"Database search error: {e}")
            return []
    
    def _search_legacy_index(self, query: str, area_name: str, k: int = 25) -> List[Dict]:
        """Legacy index'te arama yap"""
        area_data = self._load_legacy_index(area_name)
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
                if idx < len(area_data['mapping']) and idx \!= -1:
                    mapping_data = area_data['mapping'][idx]
                    results.append({
                        'decision_id': mapping_data.get('id', mapping_data.get('decision_id')),
                        'similarity_score': float(score),
                        'legal_area': area_name,
                        'mahkeme': mapping_data.get('mahkeme', ''),
                        'text_snippet': str(mapping_data.get('text', ''))[:200] + '...',
                        'type': 'legacy',
                        'karar_tarihi': mapping_data.get('karar_tarihi', '')
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"Legacy search error in {area_name}: {e}")
            return []
    
    def advanced_search(self, query: str, k: int = 25) -> Dict:
        """
        Gelişmiş hibrit arama - hem legacy hem yeni kararları birleştirir
        """
        # Hukuk alanını tespit et
        detected_areas = self.detector.get_multiple_areas(query, threshold=0.05)
        primary_area = self.detector.get_primary_area(query)
        
        results = {
            'query': query,
            'primary_area': primary_area,
            'detected_areas': detected_areas,
            'results': [],
            'search_stats': {
                'legacy': {},
                'database': {},
                'total_legacy': 0,
                'total_database': 0
            }
        }
        
        # Primary area'da ara
        k_per_source = k // 2  # Her kaynak için yarısı kadar
        
        # 1. Legacy index'te ara
        legacy_results = self._search_legacy_index(query, primary_area, k_per_source)
        results['results'].extend(legacy_results)
        results['search_stats']['legacy'][primary_area] = len(legacy_results)
        results['search_stats']['total_legacy'] += len(legacy_results)
        
        # 2. Database'de ara
        db_results = self._search_database_decisions(query, primary_area, k_per_source)
        results['results'].extend(db_results)
        results['search_stats']['database'][primary_area] = len(db_results)
        results['search_stats']['total_database'] += len(db_results)
        
        # 3. Eğer yeterli sonuç yoksa diğer alanlarda da ara
        if len(results['results']) < k and len(detected_areas) > 1:
            remaining_k = k - len(results['results'])
            per_area_k = max(3, remaining_k // (len(detected_areas) - 1))
            
            for area in detected_areas[1:3]:  # En fazla 2 ek alan
                if area \!= primary_area and area in self.detector.available_areas:
                    # Legacy'den ara
                    area_legacy = self._search_legacy_index(query, area, per_area_k // 2)
                    results['results'].extend(area_legacy)
                    results['search_stats']['legacy'][area] = len(area_legacy)
                    results['search_stats']['total_legacy'] += len(area_legacy)
                    
                    # Database'den ara
                    area_db = self._search_database_decisions(query, area, per_area_k // 2)
                    results['results'].extend(area_db)
                    results['search_stats']['database'][area] = len(area_db)
                    results['search_stats']['total_database'] += len(area_db)
        
        # 4. Sonuçları score'a göre sırala ve deduplike et
        seen_ids = set()
        unique_results = []
        
        for result in sorted(results['results'], key=lambda x: x['similarity_score'], reverse=True):
            decision_id = result['decision_id']
            if decision_id not in seen_ids:
                seen_ids.add(decision_id)
                unique_results.append(result)
                
        results['results'] = unique_results[:k]
        results['total_found'] = len(results['results'])
        results['sources_used'] = {
            'legacy_indexes': results['search_stats']['total_legacy'],
            'database_search': results['search_stats']['total_database']
        }
        
        logger.info(f"Advanced search: '{query}' -> {results['total_found']} results (Legacy: {results['search_stats']['total_legacy']}, DB: {results['search_stats']['total_database']})")
        
        return results
