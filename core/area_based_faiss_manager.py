import os
import pickle
import faiss
import numpy as np
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
import logging
from django.conf import settings
from .models import JudicialDecision
from .legal_area_detector import LegalAreaDetector

logger = logging.getLogger(__name__)

class AreaBasedFAISSManager:
    def __init__(self):
        self.base_path = '/var/www/judicial_platform/faiss_dizinleri'
        self.detector = LegalAreaDetector()
        self.embedding_model = None
        
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
        
    def add_decision_to_area_index(self, decision_id: int, legal_area: str):
        """Yeni karar\u0131 belirtilen hukuk alan\u0131na ekler"""
        try:
            decision = JudicialDecision.objects.get(id=decision_id)
            
            # Metin hazırla
            text = (decision.karar_ozeti or '') + ' ' + (decision.karar_tam_metni or '')
            if len(text.strip()) < 10:
                return False
                
            # Index dosya yolları
            index_file = os.path.join(self.base_path, f'faiss_{legal_area}.index')
            mapping_file = os.path.join(self.base_path, f'mapping_{legal_area}.pkl')
            
            # Embedding oluştur
            model = self._get_embedding_model()
            if not model:
                return False
                
            text_embedding = model.encode([text])
            text_embedding = text_embedding.astype('float32')
            
            # Index ve mapping'i yükle/oluştur
            if os.path.exists(index_file) and os.path.exists(mapping_file):
                # Mevcut index'i yükle
                faiss_index = faiss.read_index(index_file)
                with open(mapping_file, 'rb') as f:
                    mapping = pickle.load(f)
            else:
                # Yeni index oluştur
                dimension = text_embedding.shape[1]
                faiss_index = faiss.IndexFlatIP(dimension)
                mapping = []
            
            # Yeni karar\u0131 ekle
            faiss_index.add(text_embedding)
            mapping.append({
                'id': decision.id,
                'decision_id': decision.id,
                'mahkeme': decision.karar_veren_mahkeme or '',
                'text': text,
                'karar_tarihi': str(decision.karar_tarihi) if decision.karar_tarihi else '',
                'legal_area': legal_area
            })
            
            # Kaydet
            faiss.write_index(faiss_index, index_file)
            with open(mapping_file, 'wb') as f:
                pickle.dump(mapping, f)
                
            logger.info(f"Added decision {decision_id} to {legal_area} index")
            return True
            
        except Exception as e:
            logger.error(f"Error adding decision {decision_id} to {legal_area}: {e}")
            return False
    
    def process_new_decisions(self, limit: int = 1000):
        """Henüz alan\u0131 tespit edilmemiş kararları işler"""
        
        # Henüz legal_area'sı olmayan kararları bul
        unprocessed = JudicialDecision.objects.filter(
            detected_legal_area__isnull=True
        )[:limit]
        
        if not unprocessed.exists():
            logger.info("No unprocessed decisions found")
            return {'processed': 0, 'added_to_index': 0}
            
        processed = 0
        added_to_index = 0
        
        for decision in unprocessed:
            try:
                # 1. Hukuk alanını tespit et
                text = (decision.karar_ozeti or '') + ' ' + (decision.karar_tam_metni or '')
                legal_area = self.detector.get_primary_area(text)
                
                # 2. Legal area'yi kaydet
                decision.detected_legal_area = legal_area
                decision.save(update_fields=['detected_legal_area'])
                
                # 3. Index'e ekle
                if self.add_decision_to_area_index(decision.id, legal_area):
                    added_to_index += 1
                    
                processed += 1
                
                if processed % 100 == 0:
                    logger.info(f"Processed {processed} decisions")
                    
            except Exception as e:
                logger.error(f"Error processing decision {decision.id}: {e}")
                continue
                
        return {
            'processed': processed,
            'added_to_index': added_to_index
        }
    
    def get_area_index_stats(self):
        """Tüm alan indexlerinin istatistiklerini döndürür"""
        stats = {}
        
        for area in self.detector.available_areas:
            index_file = os.path.join(self.base_path, f'faiss_{area}.index')
            mapping_file = os.path.join(self.base_path, f'mapping_{area}.pkl')
            
            if os.path.exists(index_file) and os.path.exists(mapping_file):
                try:
                    with open(mapping_file, 'rb') as f:
                        mapping = pickle.load(f)
                    
                    stats[area] = {
                        'decision_count': len(mapping),
                        'file_size_mb': round(os.path.getsize(index_file) / 1024 / 1024, 2),
                        'last_modified': os.path.getmtime(index_file)
                    }
                except:
                    stats[area] = {'error': 'Could not load'}
                    
        return stats
    
    def sync_database_with_indexes(self):
        """Veritabanındaki legal_area bilgilerini indexlerle senkronize eder"""
        results = {
            'synced_areas': {},
            'total_synced': 0
        }
        
        # Her alan için senkronizasyon
        area_counts = {}
        for decision in JudicialDecision.objects.exclude(detected_legal_area__isnull=True):
            area = decision.detected_legal_area
            area_counts[area] = area_counts.get(area, 0) + 1
        
        for area, count in area_counts.items():
            # Bu alandaki kararları indexe ekle
            decisions_in_area = JudicialDecision.objects.filter(detected_legal_area=area)[:count]
            
            added = 0
            for decision in decisions_in_area:
                if self.add_decision_to_area_index(decision.id, area):
                    added += 1
                    
            results['synced_areas'][area] = added
            results['total_synced'] += added
            
        return results
