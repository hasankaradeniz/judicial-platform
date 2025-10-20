"""
Management command to warm up caches
Usage: python manage.py warm_cache
"""
from django.core.management.base import BaseCommand
from django.core.cache import cache
from core.models import JudicialDecision, Article
from core.views_optimized import QueryOptimizer
from random import sample
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Warm up application caches for better performance'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear cache before warming',
        )
        parser.add_argument(
            '--verbose',
            action='store_true', 
            help='Verbose output',
        )
    
    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing cache...')
            cache.clear()
        
        self.stdout.write('Starting cache warming...')
        
        try:
            # Ana sayfa cache'i
            self.warm_homepage_cache(options['verbose'])
            
            # API cache'leri
            self.warm_api_cache(options['verbose'])
            
            # Search cache'i
            self.warm_search_cache(options['verbose'])
            
            self.stdout.write(
                self.style.SUCCESS('Cache warming completed successfully!')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Cache warming failed: {str(e)}')
            )
            logger.error(f'Cache warming error: {e}')
    
    def warm_homepage_cache(self, verbose=False):
        """Ana sayfa için cache'leri ısıt"""
        if verbose:
            self.stdout.write('Warming homepage cache...')
        
        # Toplam karar sayısı
        total_decisions = JudicialDecision.objects.count()
        cache.set('home_total_decisions_v2', total_decisions, 1800)
        
        # En yeni kararlar
        newest = QueryOptimizer.get_optimized_decisions(10)
        newest_data = []
        for decision in newest:
            newest_data.append({
                'id': decision.id,
                'mahkeme': decision.karar_veren_mahkeme,
                'numara': decision.karar_numarasi,
                'tarih': decision.karar_tarihi.strftime('%Y-%m-%d') if decision.karar_tarihi else '',
                'ozet': decision.karar_ozeti[:150] + '...' if len(decision.karar_ozeti) > 150 else decision.karar_ozeti
            })
        cache.set('api_newest_decisions', newest_data, 900)
        
        # Rastgele kararlar
        random_decisions = QueryOptimizer.get_random_decisions(3)
        random_data = []
        for decision in random_decisions:
            random_data.append({
                'id': decision.id,
                'mahkeme': decision.karar_veren_mahkeme,
                'numara': decision.karar_numarasi,
                'tarih': decision.karar_tarihi.strftime('%Y-%m-%d') if decision.karar_tarihi else '',
                'ozet': decision.karar_ozeti[:200] + '...' if len(decision.karar_ozeti) > 200 else decision.karar_ozeti
            })
        cache.set('api_random_decisions', random_data, 1800)
        
        if verbose:
            self.stdout.write(f'  - Total decisions: {total_decisions}')
            self.stdout.write(f'  - Newest decisions: {len(newest_data)}')
            self.stdout.write(f'  - Random decisions: {len(random_data)}')
    
    def warm_api_cache(self, verbose=False):
        """API endpoints için cache'leri ısıt"""
        if verbose:
            self.stdout.write('Warming API cache...')
        
        # Rastgele makaleler
        all_article_ids = list(Article.objects.values_list('id', flat=True)[:1000])
        if len(all_article_ids) >= 3:
            random_ids = sample(all_article_ids, min(3, len(all_article_ids)))
            articles = Article.objects.filter(id__in=random_ids).only(
                'id', 'title', 'authors', 'journal', 'publication_date', 'abstract'
            )
            
            articles_data = []
            for article in articles:
                articles_data.append({
                    'id': article.id,
                    'title': article.title,
                    'authors': article.authors,
                    'journal': article.journal,
                    'date': article.publication_date.strftime('%Y-%m-%d') if article.publication_date else '',
                    'abstract': article.abstract[:150] + '...' if article.abstract and len(article.abstract) > 150 else article.abstract
                })
            
            cache.set('api_random_articles', articles_data, 2700)
            
            if verbose:
                self.stdout.write(f'  - Random articles: {len(articles_data)}')
        
        # Resmi Gazete cache
        try:
            from core.resmi_gazete_scraper import get_resmi_gazete_content
            rg_content = get_resmi_gazete_content()[:5]
            cache.set('api_resmi_gazete', rg_content, 3600)
            
            if verbose:
                self.stdout.write(f'  - Resmi Gazete items: {len(rg_content)}')
        except Exception as e:
            if verbose:
                self.stdout.write(f'  - Resmi Gazete error: {str(e)}')
    
    def warm_search_cache(self, verbose=False):
        """Popular search terms için cache'leri ısıt"""
        if verbose:
            self.stdout.write('Warming search cache...')
        
        popular_terms = [
            'boşanma', 'alacak', 'kira', 'iş sözleşmesi', 'tazminat',
            'miras', 'satış', 'noter', 'icra', 'dava'
        ]
        
        cached_count = 0
        for term in popular_terms:
            cache_key = f'search_results_{term}_judicial'
            if not cache.get(cache_key):
                try:
                    results = QueryOptimizer.get_search_results_optimized(
                        term, 'judicial', 10
                    )
                    cache.set(cache_key, results, 1800)
                    cached_count += 1
                except Exception as e:
                    if verbose:
                        self.stdout.write(f'  - Error caching {term}: {str(e)}')
        
        if verbose:
            self.stdout.write(f'  - Cached search terms: {cached_count}/{len(popular_terms)}')