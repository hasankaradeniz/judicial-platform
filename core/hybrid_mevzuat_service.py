# core/hybrid_mevzuat_service.py

from django.db.models import Q
from django.core.cache import cache
from django.utils import timezone
from core.models import MevzuatGelismis, MevzuatTuru, MevzuatKategori
from core.live_mevzuat_search import LiveMevzuatSearcher
import logging

logger = logging.getLogger(__name__)

class HybridMevzuatService:
    """Hibrit mevzuat arama servisi: DB + Live search"""
    
    def __init__(self):
        self.live_searcher = LiveMevzuatSearcher()
    
    def search_mevzuat(self, query, mevzuat_type=None, page=1, per_page=20):
        """Ana hibrit arama fonksiyonu"""
        try:
            # Veritabanından arama
            db_results = self._search_database(query, mevzuat_type, per_page)
            
            # Live arama - her zaman yap ama cache'li
            live_results = []
            try:
                live_results = self._search_live(query, mevzuat_type, per_page)
            except Exception as e:
                logger.error(f"Live search failed: {str(e)}")
                live_results = []
            
            # Sonuçları birleştir ve normalize et
            combined_results = self._combine_and_normalize_results(db_results, live_results, per_page)
            
            # Sayfalama uygula
            paginated_results = self._paginate_results(combined_results, page, per_page)
            
            return {
                'results': paginated_results,
                'total_count': len(combined_results),
                'db_count': len(db_results),
                'live_count': len(live_results),
                'page': page,
                'per_page': per_page,
                'has_next': len(combined_results) > (page * per_page),
                'has_previous': page > 1
            }
            
        except Exception as e:
            logger.error(f"Hybrid search error: {str(e)}")
            return {
                'results': [],
                'total_count': 0,
                'db_count': 0,
                'live_count': 0,
                'page': page,
                'per_page': per_page,
                'has_next': False,
                'has_previous': False,
                'error': str(e)
            }
    
    def _search_database(self, query, mevzuat_type, limit):
        """Veritabanından arama - iyileştirilmiş"""
        try:
            queryset = MevzuatGelismis.objects.select_related('mevzuat_turu', 'kategori')
            
            # Metin araması - çok daha esnek ve kapsamlı
            if query:
                query_words = query.lower().split()
                
                # Önce tam eşleşme ara
                exact_match = Q()
                for word in query_words:
                    exact_match &= (
                        Q(baslik__icontains=word) |
                        Q(tam_metin__icontains=word) |
                        Q(mevzuat_numarasi__icontains=word)
                    )
                
                # Sonra kısmi eşleşme ara
                partial_match = Q()
                for word in query_words:
                    if len(word) > 3:  # Kısa kelimeler hariç
                        partial_match |= (
                            Q(baslik__icontains=word) |
                            Q(tam_metin__icontains=word) |
                            Q(mevzuat_numarasi__icontains=word) |
                            Q(kategori__ad__icontains=word) |
                            Q(mevzuat_turu__ad__icontains=word)
                        )
                
                # Tek kelimeli aramalar için fuzzy matching
                single_word_match = Q()
                if len(query_words) == 1 and len(query_words[0]) > 4:
                    word = query_words[0]
                    # Benzer kelimeler için partial matching
                    single_word_match = (
                        Q(baslik__icontains=word[:4]) |  # İlk 4 harf
                        Q(baslik__icontains=word[-4:]) |  # Son 4 harf
                        Q(tam_metin__icontains=word[:5])   # İlk 5 harf tam metinde
                    )
                
                # Sonuçları birleştir - önce exact, sonra partial, sonra fuzzy
                final_query = exact_match | partial_match | single_word_match
                queryset = queryset.filter(final_query)
            
            # Tür filtresi
            if mevzuat_type:
                queryset = queryset.filter(mevzuat_turu__kod=mevzuat_type)
            
            # Sıralama - önce başlıkta eşleşen, sonra metinde eşleşen
            if query:
                queryset = queryset.extra(
                    select={
                        'title_match': "CASE WHEN LOWER(baslik) LIKE %s THEN 1 ELSE 0 END",
                        'exact_title_match': "CASE WHEN LOWER(baslik) = %s THEN 1 ELSE 0 END"
                    },
                    select_params=[f'%{query.lower()}%', query.lower()]
                ).order_by('-exact_title_match', '-title_match', 'baslik')
            
            # Sonuçları al
            results = []
            for mevzuat in queryset[:limit]:
                results.append({
                    'id': mevzuat.id,
                    'title': mevzuat.baslik,
                    'mevzuat_no': mevzuat.mevzuat_numarasi,
                    'type': mevzuat.mevzuat_turu.ad if mevzuat.mevzuat_turu else '',
                    'date': mevzuat.yayin_tarihi.strftime('%d.%m.%Y') if mevzuat.yayin_tarihi else '',
                    'rg_date': mevzuat.resmi_gazete_tarihi.strftime('%d.%m.%Y') if mevzuat.resmi_gazete_tarihi else '',
                    'rg_number': mevzuat.resmi_gazete_sayisi,
                    'preview_text': mevzuat.tam_metin[:300] + '...' if len(mevzuat.tam_metin) > 300 else mevzuat.tam_metin,
                    'url': f'/legislation/{mevzuat.id}/',
                    'source': 'database',
                    'full_text_available': True,
                    'created_date': mevzuat.kayit_tarihi.isoformat() if mevzuat.kayit_tarihi else None
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Database search error: {str(e)}")
            return []
    
    def _search_live(self, query, mevzuat_type, limit):
        """Canlı aramadan sonuçları al"""
        try:
            # Live search yap
            live_results = self.live_searcher.search_mevzuat(query, mevzuat_type, limit)
            
            # Sonuçları normalize et
            normalized_results = []
            for result in live_results:
                normalized_results.append({
                    'id': f"live_{result.get('mevzuat_no', 'unknown')}",
                    'title': result.get('title', 'Başlıksız'),
                    'mevzuat_no': result.get('mevzuat_no', ''),
                    'type': result.get('type', 'Mevzuat'),
                    'date': result.get('date', ''),
                    'rg_date': result.get('rg_date', ''),
                    'rg_number': result.get('rg_number', ''),
                    'preview_text': result.get('preview_text', ''),
                    'url': result.get('url', ''),
                    'source': 'live',
                    'full_text_available': False,
                    'external_url': result.get('url', '')
                })
            
            return normalized_results
            
        except Exception as e:
            logger.error(f"Live search error: {str(e)}")
            return []
    
    def _combine_and_normalize_results(self, db_results, live_results, limit):
        """Sonuçları birleştir ve duplicate'leri kaldır"""
        try:
            combined = []
            seen_titles = set()
            seen_numbers = set()
            
            # Önce veritabanı sonuçlarını ekle
            for result in db_results:
                title_key = self._normalize_title_for_comparison(result['title'])
                number_key = result['mevzuat_no']
                
                if title_key not in seen_titles and number_key not in seen_numbers:
                    combined.append(result)
                    seen_titles.add(title_key)
                    if number_key:
                        seen_numbers.add(number_key)
            
            # Sonra live sonuçları ekle (çok daha esnek duplicate kontrolü)
            for result in live_results:
                title_key = self._normalize_title_for_comparison(result['title'])
                number_key = result['mevzuat_no']
                
                # Çok sıkı duplicate kontrolü: sadece tam aynı numara VE başlık
                is_duplicate = False
                if number_key and title_key:
                    # Hem numara hem başlık aynıysa duplicate
                    for existing in combined:
                        existing_title_key = self._normalize_title_for_comparison(existing['title'])
                        existing_number_key = existing['mevzuat_no']
                        
                        if (number_key == existing_number_key and 
                            title_key == existing_title_key):
                            is_duplicate = True
                            logger.info(f"Exact duplicate found: {result['title']} (Number: {number_key})")
                            break
                
                # Farklı başlık veya farklı numaraysa göster
                if not is_duplicate and len(combined) < limit * 3:  # Daha fazla sonuç için
                    result['is_live'] = True  # Live sonuç işaretleme
                    combined.append(result)
                    seen_titles.add(title_key)
                    if number_key:
                        seen_numbers.add(number_key)
                    logger.info(f"Added live result: {result['title']} (ID: {result['id']})")
                else:
                    if is_duplicate:
                        logger.info(f"Skipped exact duplicate: {result['title']} (Number: {number_key})")
                    else:
                        logger.info(f"Skipped due to limit: {result['title']} (Number: {number_key})")
            
            # Sonuçları relevance'a göre sırala
            # DB sonuçları önce gelsin, sonra live sonuçlar
            combined.sort(key=lambda x: (
                0 if x['source'] == 'database' else 1,  # DB önce
                -len(x['title']),  # Uzun başlıklar önce
                x['title'].lower()  # Alfabetik
            ))
            
            return combined[:limit * 2]  # Fazladan sonuç için
            
        except Exception as e:
            logger.error(f"Combine results error: {str(e)}")
            return db_results + live_results
    
    def _normalize_title_for_comparison(self, title):
        """Başlığı karşılaştırma için normalize et"""
        if not title:
            return ""
        
        # Küçük harfe çevir, noktalama işaretlerini kaldır
        normalized = title.lower()
        normalized = ''.join(c for c in normalized if c.isalnum() or c.isspace())
        normalized = ' '.join(normalized.split())  # Fazla boşlukları temizle
        
        return normalized
    
    def _paginate_results(self, results, page, per_page):
        """Sonuçları sayfalara böl"""
        try:
            start_index = (page - 1) * per_page
            end_index = start_index + per_page
            
            return results[start_index:end_index]
            
        except Exception as e:
            logger.error(f"Pagination error: {str(e)}")
            return results
    
    def get_mevzuat_by_number(self, mevzuat_number, mevzuat_type=None):
        """Mevzuat numarasıyla spesifik arama"""
        try:
            # Önce veritabanından ara
            db_result = None
            try:
                queryset = MevzuatGelismis.objects.select_related('mevzuat_turu', 'kategori')
                queryset = queryset.filter(mevzuat_numarasi=mevzuat_number)
                
                if mevzuat_type:
                    queryset = queryset.filter(mevzuat_turu__kod=mevzuat_type)
                
                mevzuat = queryset.first()
                if mevzuat:
                    db_result = {
                        'id': mevzuat.id,
                        'title': mevzuat.baslik,
                        'mevzuat_no': mevzuat.mevzuat_numarasi,
                        'type': mevzuat.mevzuat_turu.ad if mevzuat.mevzuat_turu else '',
                        'full_text': mevzuat.tam_metin,
                        'date': mevzuat.yayin_tarihi,
                        'rg_date': mevzuat.resmi_gazete_tarihi,
                        'rg_number': mevzuat.resmi_gazete_sayisi,
                        'source': 'database',
                        'url': f'/legislation/{mevzuat.id}/'
                    }
            except Exception as e:
                logger.error(f"DB number search error: {str(e)}")
            
            # Veritabanında bulunamadıysa live ara
            if not db_result:
                live_results = self.live_searcher.search_by_number(mevzuat_number, mevzuat_type)
                if live_results:
                    return live_results[0]
            
            return db_result
            
        except Exception as e:
            logger.error(f"Number search error: {str(e)}")
            return None
    
    def get_statistics(self):
        """Sistem istatistikleri"""
        try:
            stats = {
                'total_db_mevzuat': MevzuatGelismis.objects.count(),
                'db_by_type': {},
                'cache_info': {},
                'last_updated': timezone.now().isoformat()
            }
            
            # Türlere göre sayım
            for mevzuat_type in MevzuatTuru.objects.all():
                count = MevzuatGelismis.objects.filter(mevzuat_turu=mevzuat_type).count()
                stats['db_by_type'][mevzuat_type.ad] = count
            
            return stats
            
        except Exception as e:
            logger.error(f"Statistics error: {str(e)}")
            return {}
    
    def clear_search_cache(self):
        """Arama cache'ini temizle"""
        try:
            self.live_searcher.clear_cache()
            cache.delete_pattern("hybrid_search_*")
            return True
        except Exception as e:
            logger.error(f"Cache clear error: {str(e)}")
            return False