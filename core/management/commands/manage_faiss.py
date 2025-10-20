"""
FAISS dizin yönetimi için management command
Usage: python manage.py manage_faiss [action]
"""
from django.core.management.base import BaseCommand, CommandError
from core.faiss_manager import faiss_manager
from core.tasks import update_faiss_index, rebuild_faiss_index_full, check_index_health
from django.utils import timezone
import json

class Command(BaseCommand):
    help = 'FAISS index management commands'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'action',
            choices=['status', 'update', 'rebuild', 'check', 'stats', 'auto-update'],
            help='Action to perform'
        )
        parser.add_argument(
            '--async',
            action='store_true',
            help='Run task asynchronously with Celery'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force action even if not needed'
        )
    
    def handle(self, *args, **options):
        action = options['action']
        use_async = options['async']
        force = options['force']
        
        self.stdout.write(f'\n🔍 FAISS Index Management - Action: {action.upper()}\n')
        
        if action == 'status':
            self.show_status()
        elif action == 'update':
            self.update_index(use_async, force)
        elif action == 'rebuild':
            self.rebuild_index(use_async)
        elif action == 'check':
            self.check_health(use_async)
        elif action == 'stats':
            self.show_detailed_stats()
        elif action == 'auto-update':
            self.auto_update()
    
    def show_status(self):
        """Index durumunu göster"""
        stats = faiss_manager.get_index_stats()
        
        self.stdout.write("📊 FAISS Index Status:")
        self.stdout.write("-" * 40)
        
        if stats['exists']:
            self.stdout.write(self.style.SUCCESS(f"✅ Index exists: YES"))
            self.stdout.write(f"📁 Size: {stats['size_mb']} MB")
            self.stdout.write(f"📄 Decisions indexed: {stats['decision_count']:,}")
            
            if stats['last_update']:
                self.stdout.write(f"🕐 Last update: {stats['last_update']}")
            else:
                self.stdout.write(self.style.WARNING("⚠️  Last update: UNKNOWN"))
        else:
            self.stdout.write(self.style.ERROR("❌ Index exists: NO"))
        
        # Database comparison
        from core.models import JudicialDecision
        db_count = JudicialDecision.objects.count()
        self.stdout.write(f"🗄️  Database decisions: {db_count:,}")
        
        if stats['exists']:
            diff = db_count - stats['decision_count']
            if diff > 0:
                self.stdout.write(self.style.WARNING(f"⚠️  Missing from index: {diff:,} decisions"))
            elif diff < 0:
                self.stdout.write(self.style.WARNING(f"⚠️  Extra in index: {abs(diff):,} decisions"))
            else:
                self.stdout.write(self.style.SUCCESS("✅ Database and index in sync"))
    
    def update_index(self, use_async, force):
        """Index'i güncelle"""
        if use_async:
            self.stdout.write("🚀 Starting async index update...")
            task = update_faiss_index.delay()
            self.stdout.write(f"📋 Task ID: {task.id}")
            self.stdout.write("⏳ Task submitted to Celery queue")
        else:
            self.stdout.write("🔄 Starting synchronous index update...")
            
            if force or faiss_manager.should_rebuild_index():
                if faiss_manager.should_rebuild_index() and not force:
                    self.stdout.write("🔨 Full rebuild required...")
                    success = faiss_manager.build_index_full()
                else:
                    self.stdout.write("⚡ Incremental update...")
                    success = faiss_manager.update_index_incremental()
                
                if success:
                    self.stdout.write(self.style.SUCCESS("✅ Index update completed"))
                    self.show_status()
                else:
                    self.stdout.write(self.style.ERROR("❌ Index update failed"))
            else:
                self.stdout.write(self.style.WARNING("⏭️  Index update not needed"))
    
    def rebuild_index(self, use_async):
        """Index'i tamamen yeniden oluştur"""
        if use_async:
            self.stdout.write("🚀 Starting async full rebuild...")
            task = rebuild_faiss_index_full.delay()
            self.stdout.write(f"📋 Task ID: {task.id}")
        else:
            self.stdout.write("🔨 Starting full index rebuild...")
            self.stdout.write(self.style.WARNING("⚠️  This may take several minutes..."))
            
            success = faiss_manager.build_index_full()
            
            if success:
                self.stdout.write(self.style.SUCCESS("✅ Full rebuild completed"))
                self.show_status()
            else:
                self.stdout.write(self.style.ERROR("❌ Full rebuild failed"))
    
    def check_health(self, use_async):
        """Index sağlığını kontrol et"""
        if use_async:
            self.stdout.write("🚀 Starting async health check...")
            task = check_index_health.delay()
            self.stdout.write(f"📋 Task ID: {task.id}")
        else:
            self.stdout.write("🏥 Checking index health...")
            
            # Direct health check
            stats = faiss_manager.get_index_stats()
            
            from core.models import JudicialDecision
            db_count = JudicialDecision.objects.count()
            
            issues = []
            
            if not stats['exists']:
                issues.append("❌ Index file does not exist")
            elif stats['decision_count'] == 0:
                issues.append("❌ Index is empty")
            elif db_count > stats['decision_count'] + 50:
                issues.append(f"⚠️  Index missing {db_count - stats['decision_count']} decisions")
            
            if issues:
                self.stdout.write(self.style.ERROR("🚨 Health check found issues:"))
                for issue in issues:
                    self.stdout.write(f"   {issue}")
            else:
                self.stdout.write(self.style.SUCCESS("✅ Index health check passed"))
    
    def show_detailed_stats(self):
        """Detaylı istatistikleri göster"""
        import os
        from core.models import JudicialDecision
        
        self.stdout.write("📈 Detailed FAISS Statistics:")
        self.stdout.write("=" * 50)
        
        stats = faiss_manager.get_index_stats()
        
        # File system stats
        if stats['exists']:
            index_path = faiss_manager.index_file
            metadata_path = faiss_manager.metadata_file
            
            self.stdout.write(f"📂 Index file: {index_path}")
            self.stdout.write(f"📂 Metadata file: {metadata_path}")
            self.stdout.write(f"💾 Index size: {stats['size_mb']} MB")
            
            if os.path.exists(metadata_path):
                metadata_size = os.path.getsize(metadata_path) / 1024 / 1024
                self.stdout.write(f"💾 Metadata size: {metadata_size:.2f} MB")
        
        # Database stats
        total_decisions = JudicialDecision.objects.count()
        recent_decisions = JudicialDecision.objects.filter(
            created_at__gte=timezone.now() - timezone.timedelta(days=7)
        ).count()
        
        self.stdout.write(f"🗄️  Total decisions in DB: {total_decisions:,}")
        self.stdout.write(f"📅 Recent decisions (7 days): {recent_decisions:,}")
        
        # Search performance estimate
        if stats['exists']:
            decisions_per_mb = stats['decision_count'] / max(stats['size_mb'], 1)
            self.stdout.write(f"⚡ Density: {decisions_per_mb:.0f} decisions/MB")
    
    def auto_update(self):
        """Otomatik güncelleme logic'i"""
        self.stdout.write("🤖 Auto-update analysis:")
        
        should_rebuild = faiss_manager.should_rebuild_index()
        
        if should_rebuild:
            self.stdout.write("🔄 Auto-update triggered")
            self.update_index(use_async=False, force=False)
        else:
            self.stdout.write(self.style.SUCCESS("✅ No update needed"))
            
        # Health check
        self.check_health(use_async=False)