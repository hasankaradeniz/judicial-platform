import logging
from django.core.cache import cache

logger = logging.getLogger(__name__)

class WorkingMevzuatSearcher:
    """Çalışan mevzuat arama sistemi - mock veriler ile"""
    
    def __init__(self):
        self.base_url = "https://www.mevzuat.gov.tr"
        
    def search_legislation(self, query, mevzuat_type=None, page=1, per_page=20):
        """Ana arama fonksiyonu"""
        try:
            logger.info(f"Working search için arama yapılıyor: {query}")
            
            # Cache kontrolü
            cache_key = f"working_search_{query}_{mevzuat_type}_{page}".replace(' ', '_')
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.info(f"Cache'den sonuç: {query}")
                return cached_result
            
            # Mock sonuçlar oluştur
            results = self._create_mock_results(query)
            
            # Sayfalama
            total_count = len(results)
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            paginated_results = results[start_idx:end_idx]
            
            search_results = {
                'results': paginated_results,
                'total_count': total_count,
                'page': page,
                'per_page': per_page,
                'has_next': end_idx < total_count,
                'has_previous': page > 1,
                'source': 'working_mock'
            }
            
            # Cache'e kaydet
            if results:
                cache.set(cache_key, search_results, 1800)  # 30 dakika
            
            logger.info(f"Working search sonucu: {len(paginated_results)} sonuç döndürüldü")
            return search_results
            
        except Exception as e:
            logger.error(f"Working search error: {str(e)}")
            return {
                'results': [],
                'total_count': 0,
                'page': page,
                'per_page': per_page,
                'has_next': False,
                'has_previous': False,
                'error': str(e)
            }
    
    def _create_mock_results(self, query):
        """Query'ye göre mock sonuçlar oluştur"""
        query_lower = query.lower()
        results = []
        
        # Ana kanunlar veritabanı
        law_database = {
            'borçlar': [
                {
                    'title': 'TÜRK BORÇLAR KANUNU',
                    'mevzuat_no': '6098',
                    'type': 'Kanun',
                    'rg_date': '04.02.2011',
                    'rg_number': '27836',
                },
                {
                    'title': 'TÜRK BORÇLAR KANUNUNUN YÜRÜRLÜĞÜ VE UYGULAMA ŞEKLİ HAKKINDA KANUN',
                    'mevzuat_no': '6101',
                    'type': 'Kanun',
                    'rg_date': '04.02.2011',
                    'rg_number': '27836',
                }
            ],
            'medeni': [
                {
                    'title': 'TÜRK MEDENİ KANUNU',
                    'mevzuat_no': '4721',
                    'type': 'Kanun',
                    'rg_date': '08.12.2001',
                    'rg_number': '24607',
                }
            ],
            'ceza': [
                {
                    'title': 'TÜRK CEZA KANUNU',
                    'mevzuat_no': '5237',
                    'type': 'Kanun',
                    'rg_date': '12.10.2004',
                    'rg_number': '25611',
                },
                {
                    'title': 'CEZA MUHAKEMESİ KANUNU',
                    'mevzuat_no': '5271',
                    'type': 'Kanun',
                    'rg_date': '17.12.2004',
                    'rg_number': '25673',
                },
                {
                    'title': 'CEZA İNFAZ KURUMLAYI VE TEDBİR',
                    'mevzuat_no': '5275',
                    'type': 'Kanun',
                    'rg_date': '29.12.2004',
                    'rg_number': '25685',
                },
                {
                    'title': 'KABAHATLER KANUNU',
                    'mevzuat_no': '5326',
                    'type': 'Kanun',
                    'rg_date': '18.03.2005',
                    'rg_number': '25772',
                },
                {
                    'title': 'TERÖRİZMİN FİNANSMANININ ÖNLENMESİ HAKKINDA KANUN',
                    'mevzuat_no': '5549',
                    'type': 'Kanun',
                    'rg_date': '18.10.2006',
                    'rg_number': '26323',
                },
                {
                    'title': 'SUÇTAN KAYNAKLANAN MALLARA EL KOYMA KANUNU',
                    'mevzuat_no': '4422',
                    'type': 'Kanun',
                    'rg_date': '04.08.1999',
                    'rg_number': '23785',
                },
                {
                    'title': 'ADALET MESLEK ELEMANLARI KANUNU',
                    'mevzuat_no': '1802',
                    'type': 'Kanun',
                    'rg_date': '24.03.1973',
                    'rg_number': '14460',
                }
            ],
            'ticaret': [
                {
                    'title': 'TÜRK TİCARET KANUNU',
                    'mevzuat_no': '6102',
                    'type': 'Kanun',
                    'rg_date': '14.02.2011',
                    'rg_number': '27846',
                },
                {
                    'title': 'REKABETIN KORUNMASI HAKKINDA KANUN',
                    'mevzuat_no': '4054',
                    'type': 'Kanun',
                    'rg_date': '13.12.1994',
                    'rg_number': '22140',
                },
                {
                    'title': 'ENDÜSTRİYEL TASARIM HAKKINDA KANUN HÜKMÜNDE KARARNAME',
                    'mevzuat_no': '554',
                    'type': 'KHK',
                    'rg_date': '27.06.1995',
                    'rg_number': '22326',
                }
            ],
            'iş': [
                {
                    'title': 'İŞ KANUNU',
                    'mevzuat_no': '4857',
                    'type': 'Kanun',
                    'rg_date': '22.05.2003',
                    'rg_number': '25134',
                },
                {
                    'title': 'İŞ SAĞLIĞI VE GÜVENLİĞİ KANUNU',
                    'mevzuat_no': '6331',
                    'type': 'Kanun',
                    'rg_date': '30.06.2012',
                    'rg_number': '28339',
                },
                {
                    'title': 'TOPLU İŞ SÖZLEŞMESİ, GREVİ VE LOK-AVT KANUNU',
                    'mevzuat_no': '6356',
                    'type': 'Kanun',
                    'rg_date': '07.11.2012',
                    'rg_number': '28460',
                },
                {
                    'title': 'SENDİKALAR VE TOPLU İŞ SÖZLEŞMESİ KANUNU',
                    'mevzuat_no': '6356',
                    'type': 'Kanun',
                    'rg_date': '07.11.2012',
                    'rg_number': '28460',
                }
            ],
            'anayasa': [
                {
                    'title': 'TÜRKİYE CUMHURİYETİ ANAYASASI',
                    'mevzuat_no': '2709',
                    'type': 'Anayasa',
                    'rg_date': '09.11.1982',
                    'rg_number': '17863',
                }
            ],
            'vergi': [
                {
                    'title': 'GELİR VERGİSİ KANUNU',
                    'mevzuat_no': '193',
                    'type': 'Kanun',
                    'rg_date': '06.01.1961',
                    'rg_number': '10700',
                },
                {
                    'title': 'KATMA DEĞER VERGİSİ KANUNU',
                    'mevzuat_no': '3065',
                    'type': 'Kanun',
                    'rg_date': '02.11.1984',
                    'rg_number': '18563',
                }
            ],
            'trafik': [
                {
                    'title': 'KARAYOLLARI TRAFİK KANUNU',
                    'mevzuat_no': '2918',
                    'type': 'Kanun',
                    'rg_date': '18.10.1983',
                    'rg_number': '18195',
                }
            ],
            'tüketici': [
                {
                    'title': 'TÜKETİCİNİN KORUNMASI HAKKINDA KANUN',
                    'mevzuat_no': '6502',
                    'type': 'Kanun',
                    'rg_date': '28.11.2013',
                    'rg_number': '28835',
                }
            ],
            'sosyal': [
                {
                    'title': 'SOSYAL GÜVENLİK VE GENEL SAĞLIK SİGORTASI KANUNU',
                    'mevzuat_no': '5510',
                    'type': 'Kanun',
                    'rg_date': '16.06.2006',
                    'rg_number': '26200',
                }
            ],
            'icra': [
                {
                    'title': 'İCRA VE İFLAS KANUNU',
                    'mevzuat_no': '2004',
                    'type': 'Kanun',
                    'rg_date': '19.06.1932',
                    'rg_number': '2128',
                }
            ],
            'belediye': [
                {
                    'title': 'BELEDİYE KANUNU',
                    'mevzuat_no': '5393',
                    'type': 'Kanun',
                    'rg_date': '13.07.2005',
                    'rg_number': '25874',
                },
                {
                    'title': 'BÜYÜKŞEH­İR BELEDİYESİ KANUNU',
                    'mevzuat_no': '5216',
                    'type': 'Kanun',
                    'rg_date': '23.07.2004',
                    'rg_number': '25531',
                }
            ],
            'çevre': [
                {
                    'title': 'ÇEVRE KANUNU',
                    'mevzuat_no': '2872',
                    'type': 'Kanun',
                    'rg_date': '11.08.1983',
                    'rg_number': '18132',
                },
                {
                    'title': 'ORMAN KANUNU',
                    'mevzuat_no': '6831',
                    'type': 'Kanun',
                    'rg_date': '08.09.1956',
                    'rg_number': '9402',
                }
            ],
            'eğitim': [
                {
                    'title': 'MİLLI EĞİTİM TEMEL KANUNU',
                    'mevzuat_no': '1739',
                    'type': 'Kanun',
                    'rg_date': '24.06.1973',
                    'rg_number': '14574',
                },
                {
                    'title': 'YÜKSEKÖĞRETİM KANUNU',
                    'mevzuat_no': '2547',
                    'type': 'Kanun',
                    'rg_date': '06.11.1981',
                    'rg_number': '17506',
                }
            ],
            'sağlık': [
                {
                    'title': 'UMUMI HIFZISSIHHA KANUNU',
                    'mevzuat_no': '1593',
                    'type': 'Kanun',
                    'rg_date': '06.05.1930',
                    'rg_number': '1489',
                },
                {
                    'title': 'TIBBİ DEONTOLOJİ NİZAMNAMESİ',
                    'mevzuat_no': '1219',
                    'type': 'Nizamname',
                    'rg_date': '19.02.1953',
                    'rg_number': '8339',
                }
            ],
            'kira': [
                {
                    'title': 'TÜRK BORÇLAR KANUNU - KİRA SÖZLEŞMESİ HÜKÜMLERİ',
                    'mevzuat_no': '6098',
                    'type': 'Kanun (İlgili Bölüm)',
                    'rg_date': '04.02.2011',
                    'rg_number': '27836',
                }
            ]
        }
        
        # Query'de geçen anahtar kelimeleri ara
        found_laws = []
        for keyword, laws in law_database.items():
            if keyword in query_lower:
                found_laws.extend(laws)
        
        # Eğer spesifik kanun bulunamazsa, genel arama
        if not found_laws:
            # Query'de sayı var mı kontrol et (kanun numarası olabilir)
            import re
            numbers = re.findall(r'\d{3,5}', query)
            
            if numbers:
                # Sayı bazlı arama
                for num in numbers:
                    if num == '6098':
                        found_laws.extend(law_database['borçlar'])
                    elif num == '4721':
                        found_laws.extend(law_database['medeni'])
                    elif num == '5237':
                        found_laws.extend(law_database['ceza'])
            
            # Hala bulamazsa genel sonuçlar
            if not found_laws:
                found_laws = [
                    {
                        'title': f'{query.upper()} ile ilgili mevzuat araması',
                        'mevzuat_no': '1001',
                        'type': 'Arama Sonucu',
                        'rg_date': '',
                        'rg_number': '',
                    }
                ]
        
        # Sonuçları formatla
        for law in found_laws:
            mevzuat_no = law['mevzuat_no']
            
            # PDF URL - kendi sistemimizde açılacak
            internal_url = f"/mevzuat/pdf/?MevzuatNo={mevzuat_no}&MevzuatTur=1&MevzuatTertip=5"
            external_url = f"https://www.mevzuat.gov.tr/mevzuat?MevzuatNo={mevzuat_no}&MevzuatTur=1&MevzuatTertip=5"
            
            result = {
                'title': law['title'],
                'url': internal_url,  # Kendi sistemimizde açılacak
                'external_url': external_url,  # Dış link
                'mevzuat_no': mevzuat_no,
                'type': law['type'],
                'rg_date': law['rg_date'],
                'rg_number': law['rg_number'],
                'source': 'working_mock',
                'has_previous_versions': bool(mevzuat_no and len(mevzuat_no) > 3),
                'search_query': query
            }
            
            results.append(result)
        
        logger.info(f"Mock sonuçlar oluşturuldu: {len(results)} adet")
        for r in results[:3]:
            logger.info(f"- {r['title'][:50]}... (No: {r['mevzuat_no']})")
        
        return results

# Kullanım için alias
SimpleMevzuatSearcher = WorkingMevzuatSearcher