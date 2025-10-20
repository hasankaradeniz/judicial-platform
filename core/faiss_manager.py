"""
FAISS Index Manager - Otomatik dizin yönetimi
"""
import os
import logging
import pickle
import hashlib
from datetime import datetime, timedelta
from django.conf import settings
from django.core.cache import cache
from django.db.models import Q
from .models import JudicialDecision
import numpy as np
import faiss

logger = logging.getLogger(__name__)

class FAISSManager:
    """FAISS dizinlerini otomatik yöneten sınıf"""
    
    def __init__(self):
        self.base_path = getattr(settings, 'FAISS_INDEX_PATH', '/var/www/judicial_platform/faiss_dizinleri')
        self.index_file = os.path.join(self.base_path, 'judicial_decisions.index')
        self.metadata_file = os.path.join(self.base_path, 'metadata.pkl')
        self.embedding_model = None
        self.index = None
        self.last_update_file = os.path.join(self.base_path, 'last_update.txt')
        
        # Ensure directory exists
        os.makedirs(self.base_path, exist_ok=True)
    
    def should_rebuild_index(self):
        """Dizinin yeniden oluşturulması gerekip gerekmediğini kontrol et"""
        try:
            # Son güncelleme zamanını kontrol et
            if os.path.exists(self.last_update_file):
                with open(self.last_update_file, 'r') as f:
                    last_update_str = f.read().strip()
                    last_update = datetime.fromisoformat(last_update_str)
                    
                    # 24 saatten eski ise yenile
                    if datetime.now() - last_update > timedelta(hours=24):
                        return True
            else:
                return True
            
            # Yeni karar sayısını kontrol et
            cache_key = 'faiss_last_decision_count'
            last_count = cache.get(cache_key, 0)
            current_count = JudicialDecision.objects.count()
            
            if current_count > last_count + 10:  # 10+ yeni karar varsa güncelle
                cache.set(cache_key, current_count, 86400)  # 24 saat
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Index rebuild check error: {e}")
            return True
    
    def get_new_decisions(self, last_update_time=None):
        """Son güncelleme sonrası eklenen yeni kararları getir"""
        if last_update_time:
            return JudicialDecision.objects.filter(
                created_at__gt=last_update_time
            ).values('id', 'karar_ozeti', 'karar_veren_mahkeme')
        else:
            return JudicialDecision.objects.all().values('id', 'karar_ozeti', 'karar_veren_mahkeme')
    
    def create_embeddings(self, texts):
        """Metinler için embeddings oluştur"""
        try:
            # Sentence-transformers kullan
            from sentence_transformers import SentenceTransformer
            
            if self.embedding_model is None:
                model_name = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
                self.embedding_model = SentenceTransformer(model_name)
            
            embeddings = self.embedding_model.encode(texts, show_progress_bar=True)
            return embeddings.astype('float32')
            
        except Exception as e:
            logger.error(f"Embedding creation error: {e}")
            # Fallback: TF-IDF
            return self.create_tfidf_embeddings(texts)
    
    def create_tfidf_embeddings(self, texts):
        """Fallback: TF-IDF embeddings"""
        from sklearn.feature_extraction.text import TfidfVectorizer
        
        vectorizer = TfidfVectorizer(max_features=512, ngram_range=(1,2))
        embeddings = vectorizer.fit_transform(texts).toarray()
        
        # Metadata'ya vectorizer'ı kaydet
        with open(os.path.join(self.base_path, 'vectorizer.pkl'), 'wb') as f:
            pickle.dump(vectorizer, f)
            
        return embeddings.astype('float32')
    
    def build_index_full(self):
        """Tam dizin oluşturma"""
        try:
            logger.info("Starting full FAISS index build...")
            
            # Tüm kararları al
            decisions = list(self.get_new_decisions())
            
            if not decisions:
                logger.warning("No decisions found for indexing")
                return False
            
            # Metinleri hazırla
            texts = []
            metadata = []
            
            for decision in decisions:
                text = f"{decision['karar_ozeti']} {decision['karar_veren_mahkeme']}"
                texts.append(text)  # İlk 1000 karakter
                metadata.append({
                    'id': decision['id'],
                    'mahkeme': decision['karar_veren_mahkeme']
                })
            
            # Embeddings oluştur
            embeddings = self.create_embeddings(texts)
            
            # FAISS index oluştur
            dimension = embeddings.shape[1]
            
            # Index tipini seç (performans için)
            if len(embeddings) > 10000:
                # Büyük dataset için HNSW
                index = faiss.IndexHNSWFlat(dimension, 32)
                index.hnsw.efConstruction = 64
            else:
                # Küçük dataset için brute force
                index = faiss.IndexFlatIP(dimension)  # Inner Product
            
            # Normalize embeddings (cosine similarity için)
            faiss.normalize_L2(embeddings)
            
            # Index'e ekle
            index.add(embeddings)
            
            # Kaydet
            faiss.write_index(index, self.index_file)
            
            with open(self.metadata_file, 'wb') as f:
                pickle.dump(metadata, f)
            
            # Son güncelleme zamanını kaydet
            with open(self.last_update_file, 'w') as f:
                f.write(datetime.now().isoformat())
            
            logger.info(f"FAISS index built successfully with {len(embeddings)} decisions")
            return True
            
        except Exception as e:
            logger.error(f"Full index build error: {e}")
            return False
    
    def update_index_incremental(self):
        """Incremental dizin güncelleme"""
        try:
            # Son güncelleme zamanını al
            if not os.path.exists(self.last_update_file):
                return self.build_index_full()
            
            with open(self.last_update_file, 'r') as f:
                last_update_str = f.read().strip()
                last_update = datetime.fromisoformat(last_update_str)
            
            # Yeni kararları al
            new_decisions = list(self.get_new_decisions(last_update))
            
            if not new_decisions:
                logger.info("No new decisions to add to index")
                return True
            
            # Mevcut index'i yükle
            if not os.path.exists(self.index_file):
                return self.build_index_full()
            
            index = faiss.read_index(self.index_file)
            
            with open(self.metadata_file, 'rb') as f:
                metadata = pickle.load(f)
            
            # Yeni embeddings oluştur
            new_texts = []
            new_metadata = []
            
            for decision in new_decisions:
                text = f"{decision['karar_ozeti']} {decision['karar_veren_mahkeme']}"
                new_texts.append(text)
                new_metadata.append({
                    'id': decision['id'],
                    'mahkeme': decision['karar_veren_mahkeme']
                })
            
            new_embeddings = self.create_embeddings(new_texts)
            faiss.normalize_L2(new_embeddings)
            
            # Index'e ekle
            index.add(new_embeddings)
            metadata.extend(new_metadata)
            
            # Kaydet
            faiss.write_index(index, self.index_file)
            
            with open(self.metadata_file, 'wb') as f:
                pickle.dump(metadata, f)
            
            # Son güncelleme zamanını güncelle
            with open(self.last_update_file, 'w') as f:
                f.write(datetime.now().isoformat())
            
            logger.info(f"FAISS index updated with {len(new_embeddings)} new decisions")
            return True
            
        except Exception as e:
            logger.error(f"Incremental index update error: {e}")
            return False
    
    def search_similar(self, query_text, k=25):
        """Benzer kararları ara"""
        try:
            if not os.path.exists(self.index_file):
                logger.warning("FAISS index not found")
                return []
            
            # Index'i yükle
            index = faiss.read_index(self.index_file)
            
            with open(self.metadata_file, 'rb') as f:
                metadata = pickle.load(f)
            
            # Query embedding oluştur
            query_embedding = self.create_embeddings([query_text])
            faiss.normalize_L2(query_embedding)
            
            # Ara
            scores, indices = index.search(query_embedding, k)
            
            # Sonuçları hazırla
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx < len(metadata):
                    results.append({
                        'decision_id': metadata[idx]['id'],
                        'similarity_score': float(score),
                        'mahkeme': metadata[idx]['mahkeme']
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            return []
    
    def get_index_stats(self):
        """Index istatistiklerini getir"""
        try:
            stats = {
                'exists': os.path.exists(self.index_file),
                'size_mb': 0,
                'decision_count': 0,
                'last_update': None
            }
            
            if stats['exists']:
                stats['size_mb'] = round(os.path.getsize(self.index_file) / 1024 / 1024, 2)
                
                index = faiss.read_index(self.index_file)
                stats['decision_count'] = index.ntotal
                
                if os.path.exists(self.last_update_file):
                    with open(self.last_update_file, 'r') as f:
                        stats['last_update'] = f.read().strip()
            
            return stats
            
        except Exception as e:
            logger.error(f"Stats error: {e}")
            return {'exists': False, 'error': str(e)}

# Singleton instance
faiss_manager = FAISSManager()