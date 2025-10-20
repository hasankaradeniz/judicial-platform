from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Create optimized database indexes for search performance'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            self.stdout.write('Creating search indexes...')
            
            # GIN indeksleri için tsvector oluştur
            indexes = [
                # Full-text search için GIN indeksleri
                """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS core_judicialdecision_search_gin 
                ON core_judicialdecision USING GIN (
                    to_tsvector('turkish', COALESCE(karar_ozeti, '') || ' ' || 
                    COALESCE(anahtar_kelimeler, '') || ' ' || 
                    COALESCE(karar_tam_metni, ''))
                );
                """,
                
                # Tarih bazlı arama için
                """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS core_judicialdecision_date_desc 
                ON core_judicialdecision (karar_tarihi DESC NULLS LAST);
                """,
                
                # Mahkeme türü için
                """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS core_judicialdecision_court_type 
                ON core_judicialdecision (karar_turu);
                """,
                
                # Mahkeme adı için
                """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS core_judicialdecision_court_name 
                ON core_judicialdecision (karar_veren_mahkeme);
                """,
                
                # Esas ve karar numarası için
                """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS core_judicialdecision_numbers 
                ON core_judicialdecision (esas_numarasi, karar_numarasi);
                """,
                
                # Compound index for common queries
                """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS core_judicialdecision_main_search 
                ON core_judicialdecision (karar_tarihi DESC, karar_turu, karar_veren_mahkeme);
                """,
            ]
            
            for index_sql in indexes:
                try:
                    self.stdout.write(f'Creating index...')
                    cursor.execute(index_sql)
                    self.stdout.write(self.style.SUCCESS('✓ Index created'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'✗ Error: {e}'))
            
            self.stdout.write(self.style.SUCCESS('All indexes created successfully!'))