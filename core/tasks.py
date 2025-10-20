"""
Celery tasks for FAISS management
"""
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from .faiss_manager import faiss_manager
from .models import JudicialDecision
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def update_faiss_index(self):
    """FAISS dizinini güncelle - Celery task"""
    try:
        logger.info("Starting FAISS index update task")
        
        # Index güncellemesi gerekli mi kontrol et
        if faiss_manager.should_rebuild_index():
            logger.info("Full index rebuild required")
            success = faiss_manager.build_index_full()
        else:
            logger.info("Incremental index update")
            success = faiss_manager.update_index_incremental()
        
        if success:
            logger.info("FAISS index update completed successfully")
            
            # Başarı bildirimi gönder
            send_notification_email(
                subject="FAISS Index Güncellendi",
                message="FAISS dizini başarıyla güncellendi.",
                success=True
            )
            
            return {"status": "success", "message": "Index updated successfully"}
        else:
            raise Exception("Index update failed")
            
    except Exception as e:
        logger.error(f"FAISS index update failed: {e}")
        
        # Retry logic
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying task, attempt {self.request.retries + 1}")
            raise self.retry(countdown=300, exc=e)  # 5 dakika sonra tekrar dene
        
        # Max retry'a ulaştıysak email gönder
        send_notification_email(
            subject="FAISS Index Güncelleme Hatası",
            message=f"FAISS dizini güncellenemedi: {str(e)}",
            success=False
        )
        
        return {"status": "error", "message": str(e)}

@shared_task
def rebuild_faiss_index_full():
    """Tam FAISS dizin yeniden oluşturma"""
    try:
        logger.info("Starting full FAISS index rebuild")
        
        success = faiss_manager.build_index_full()
        
        if success:
            stats = faiss_manager.get_index_stats()
            message = f"FAISS tam yeniden oluşturma başarılı. {stats['decision_count']} karar indexlendi."
            
            send_notification_email(
                subject="FAISS Index Yeniden Oluşturuldu",
                message=message,
                success=True
            )
            
            return {"status": "success", "stats": stats}
        else:
            raise Exception("Full rebuild failed")
            
    except Exception as e:
        logger.error(f"Full FAISS rebuild failed: {e}")
        
        send_notification_email(
            subject="FAISS Tam Yeniden Oluşturma Hatası", 
            message=f"FAISS tam yeniden oluşturma başarısız: {str(e)}",
            success=False
        )
        
        return {"status": "error", "message": str(e)}

@shared_task
def check_index_health():
    """FAISS dizin sağlığını kontrol et"""
    try:
        stats = faiss_manager.get_index_stats()
        
        issues = []
        
        if not stats['exists']:
            issues.append("Index dosyası mevcut değil")
        
        if stats['decision_count'] == 0:
            issues.append("Index boş")
        
        # Veritabanı ile karşılaştır
        db_count = JudicialDecision.objects.count()
        index_count = stats.get('decision_count', 0)
        
        if db_count > index_count + 50:  # 50+ fark varsa
            issues.append(f"Index eksik kararlar içeriyor (DB: {db_count}, Index: {index_count})")
        
        if issues:
            message = "FAISS Index Sorunları:\n" + "\n".join(issues)
            send_notification_email(
                subject="FAISS Index Sağlık Kontrolü - Sorunlar Tespit Edildi",
                message=message,
                success=False
            )
        
        return {
            "status": "checked",
            "issues": issues,
            "stats": stats,
            "healthy": len(issues) == 0
        }
        
    except Exception as e:
        logger.error(f"Index health check failed: {e}")
        return {"status": "error", "message": str(e)}

@shared_task
def optimize_faiss_index():
    """FAISS dizinini optimize et"""
    try:
        logger.info("Starting FAISS index optimization")
        
        # Bu task index'i daha hızlı hale getirmek için
        # HNSW parametrelerini optimize edebilir
        
        import faiss
        import os
        
        index_file = faiss_manager.index_file
        
        if not os.path.exists(index_file):
            return {"status": "error", "message": "Index file not found"}
        
        # Index'i yükle
        index = faiss.read_index(index_file)
        
        # HNSW ise optimize et
        if hasattr(index, 'hnsw'):
            # Arama performansını artır
            index.hnsw.efSearch = 128  # Default: 16
            
            # Kaydet
            faiss.write_index(index, index_file)
            
            logger.info("FAISS HNSW index optimized")
        
        return {"status": "success", "message": "Index optimized"}
        
    except Exception as e:
        logger.error(f"Index optimization failed: {e}")
        return {"status": "error", "message": str(e)}

@shared_task
def warm_application_cache():
    """Uygulama cache'ini ısıt - performans için"""
    try:
        from django.core.management import call_command
        
        logger.info("Starting cache warming task")
        call_command('warm_cache')
        
        return {"status": "success", "message": "Cache warmed successfully"}
        
    except Exception as e:
        logger.error(f"Cache warming failed: {e}")
        return {"status": "error", "message": str(e)}

def send_notification_email(subject, message, success=True):
    """Admin'e bildirim emaili gönder"""
    try:
        admin_email = getattr(settings, 'ADMIN_EMAIL', 'admin@lexatech.ai')
        
        if success:
            subject = f"✅ {subject}"
        else:
            subject = f"❌ {subject}"
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[admin_email],
            fail_silently=True
        )
        
    except Exception as e:
        logger.error(f"Failed to send notification email: {e}")

# Periodic task scheduling (Celery Beat ile)
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'update-faiss-index-daily': {
        'task': 'core.tasks.update_faiss_index',
        'schedule': crontab(hour=2, minute=0),  # Her gün saat 02:00
    },
    'check-index-health-hourly': {
        'task': 'core.tasks.check_index_health', 
        'schedule': crontab(minute=0),  # Her saat başı
    },
    'optimize-index-weekly': {
        'task': 'core.tasks.optimize_faiss_index',
        'schedule': crontab(day_of_week=0, hour=3, minute=0),  # Her pazar 03:00
    },
}
@shared_task
def process_new_decisions():
    """Yeni kararları otomatik işler ve indexlere ekler"""
    try:
        from .area_based_faiss_manager import AreaBasedFAISSManager
        
        manager = AreaBasedFAISSManager()
        results = manager.process_new_decisions(limit=500)
        
        logger.info(f"Auto-processed {results['processed']} new decisions, {results['added_to_index']} added to indexes")
        return results
        
    except Exception as e:
        logger.error(f"Error in process_new_decisions task: {e}")
        return {'error': str(e)}

@shared_task        
def sync_area_indexes():
    """Alan indexlerini veritabanı ile senkronize eder"""
    try:
        from .area_based_faiss_manager import AreaBasedFAISSManager
        
        manager = AreaBasedFAISSManager()
        results = manager.sync_database_with_indexes()
        
        logger.info(f"Synced {results['total_synced']} decisions to area indexes")
        return results
        
    except Exception as e:
        logger.error(f"Error in sync_area_indexes task: {e}")
        return {'error': str(e)}
