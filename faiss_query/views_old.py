# faiss_query/views.py

import os
import pickle
import faiss
import google.generativeai as genai
import numpy as np
from django.conf import settings
from django.core.paginator import Paginator
from django.shortcuts import render, redirect
from sentence_transformers import SentenceTransformer
import markdown
import re

# FAISS dizinlerini lazy loading ile yükleyelim
FAISS_DIR = os.path.join(settings.BASE_DIR, 'faiss_dizinleri')

# Global değişkenler
index_mapping = {}
_loaded_indexes = {}
_embedding_model = None

def get_embedding_model():
    """SentenceTransformer modelini lazy loading ile yükle"""
    global _embedding_model
    if _embedding_model is None:
        try:
            _embedding_model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
        except Exception as e:
            print(f"Model yükleme hatası: {e}")
            # Fallback model
            try:
                _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
            except:
                _embedding_model = None
    return _embedding_model

def load_faiss_index(alan_adi):
    """FAISS indeksini lazy loading ile yükle"""
    if alan_adi in _loaded_indexes:
        return _loaded_indexes[alan_adi]
    
    index_path = os.path.join(FAISS_DIR, f"faiss_{alan_adi}.index")
    map_path = os.path.join(FAISS_DIR, f"mapping_{alan_adi}.pkl")
    
    try:
        if os.path.exists(index_path) and os.path.exists(map_path):
            index = faiss.read_index(index_path)
            with open(map_path, "rb") as f:
                mapping = pickle.load(f)
            
            _loaded_indexes[alan_adi] = {"index": index, "mapping": mapping}
            return _loaded_indexes[alan_adi]
    except Exception as e:
        print(f"⚠️ {alan_adi} için yükleme hatası: {e}")
    return None

def get_available_indexes():
    """Mevcut indeksleri listele"""
    if os.path.exists(FAISS_DIR):
        available_indexes = [f for f in os.listdir(FAISS_DIR) if f.endswith(".index")]
        index_mapping = {}
        for file in available_indexes:
            alan_adi = file.replace("faiss_", "").replace(".index", "")
            index_mapping[alan_adi] = None  # Placeholder
        return index_mapping
    return {}

# Gemini API'yi yapılandır (sadece gerektiğinde)
try:
    genai.configure(api_key=settings.GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel(model_name="gemini-2.5-pro-preview-03-25")
except:
    gemini_model = None

# ---------------------------
# Olay giriş view
# ---------------------------
def olay_gir(request):
    if request.method == "POST":
        olay = request.POST.get("olay")
        if olay:
            from django.core.cache import cache
            import hashlib
            
            # Sonuçları cache'le
            cache_key = f"olay_sonuc_{hashlib.md5(olay.encode()).hexdigest()}"
            cached_result = cache.get(cache_key)
            
            if cached_result:
                return render(request, 'faiss_query/karar_listesi.html', cached_result)
            
            # Embedding model'i yükle
            embedding_model = get_embedding_model()
            if not embedding_model:
                return render(request, 'faiss_query/olay_gir.html', {
                    'error': 'Embedding modeli yüklenemedi.'
                })
            
            # Olay embedding'ini oluştur
            try:
                olay_embedding = embedding_model.encode([olay])
                
                # Mevcut indeksleri al
                available_indexes = get_available_indexes()
                
                if not available_indexes:
                    return render(request, 'faiss_query/olay_gir.html', {
                        'error': 'FAISS indeksleri bulunamadı.'
                    })
                
                # Her alan için arama yap
                tum_sonuclar = []
                
                for alan_adi in available_indexes.keys():
                    faiss_data = load_faiss_index(alan_adi)
                    if faiss_data:
                        index = faiss_data["index"]
                        mapping = faiss_data["mapping"]
                        
                        # Benzerlik araması yap
                        D, I = index.search(olay_embedding, k=5)  # En benzer 5 sonuç
                        
                        for i, idx in enumerate(I[0]):
                            if idx < len(mapping):
                                karar = mapping[idx]
                                benzerlik_skoru = float(D[0][i])
                                
                                tum_sonuclar.append({
                                    'alan': alan_adi.replace('_', ' ').title(),
                                    'karar': karar,
                                    'benzerlik_skoru': benzerlik_skoru
                                })
                
                # Benzerlik skoruna göre sırala
                tum_sonuclar.sort(key=lambda x: x['benzerlik_skoru'])
                
                # En iyi 20 sonucu al
                tum_sonuclar = tum_sonuclar[:20]
                
                context = {
                    'olay': olay,
                    'sonuclar': tum_sonuclar,
                    'toplam_sonuc': len(tum_sonuclar)
                }
                
                # Sonuçları cache'le (1 saat)
                cache.set(cache_key, context, 3600)
                
                return render(request, 'faiss_query/karar_listesi.html', context)
                
            except Exception as e:
                return render(request, 'faiss_query/olay_gir.html', {
                    'error': f'Arama sırasında hata oluştu: {str(e)}'
                })
    
    return render(request, 'faiss_query/olay_gir.html')

# ---------------------------
# Karar detay view
# ---------------------------
def karar_detay(request, karar_id):
    # Bu fonksiyon için gerekli implementasyon
    context = {
        'karar_id': karar_id,
        'karar': f'Karar #{karar_id} detayları...'
    }
    return render(request, 'faiss_query/karar_detay.html', context)


# ---------------------------
# Karar listesi view
# ---------------------------
def karar_listesi(request):
    """Tüm kararları listele"""
    available_indexes = get_available_indexes()
    context = {
        "available_indexes": available_indexes,
        "total_indexes": len(available_indexes)
    }
    return render(request, "faiss_query/karar_listesi.html", context)

