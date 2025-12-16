"""
Celery tasks for FAISS management - Updated for area-based system
"""
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from .faiss_manager import faiss_manager
from .area_based_faiss_manager import AreaBasedFAISSManager
area_based_faiss_manager = AreaBasedFAISSManager()
from .legal_area_detector import LegalAreaDetector
legal_area_detector = LegalAreaDetector()
from .models import JudicialDecision
import logging
from django.core.management import call_command

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

# Alan bazlı FAISS task'ları
@shared_task(bind=True, max_retries=2)
def update_area_based_indexes(self):
    """Alan bazlı FAISS indexlerini güncelle"""
    try:
        logger.info("Starting area-based FAISS index update")
        
        # Yeni kararları tespit et ve alan bazlı indexlere ekle
        recent_decisions = JudicialDecision.objects.filter(
            detected_legal_area__isnull=False
        ).order_by('-id')[:1000]  # Son 1000 kararı kontrol et
        
        added_count = 0
        for decision in recent_decisions:
            success = area_based_faiss_manager.add_decision_to_area_index(
                decision_id=decision.id,
                legal_area=decision.detected_legal_area
            )
            if success:
                added_count += 1
        
        logger.info(f"Added {added_count} decisions to area-based indexes")
        
        send_notification_email(
            subject="Alan Bazlı FAISS Güncelleme Tamamlandı",
            message=f"Alan bazlı FAISS indeksleri güncellendi. {added_count} yeni karar eklendi.",
            success=True
        )
        
        return {"status": "success", "added_count": added_count}
        
    except Exception as e:
        logger.error(f"Area-based index update failed: {e}")
        
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=600, exc=e)
        
        send_notification_email(
            subject="Alan Bazlı FAISS Güncelleme Hatası",
            message=f"Alan bazlı indeks güncelleme başarısız: {str(e)}",
            success=False
        )
        
        return {"status": "error", "message": str(e)}

@shared_task
def detect_legal_areas_bulk(batch_size=1000, max_decisions=None):
    """Toplu hukuk alanı tespiti"""
    try:
        logger.info("Starting bulk legal area detection")
        
        # Henüz legal area tespit edilmeyen kararları al
        queryset = JudicialDecision.objects.filter(detected_legal_area__isnull=True)
        
        if max_decisions:
            queryset = queryset[:max_decisions]
        
        total_count = queryset.count()
        if total_count == 0:
            logger.info("No decisions found for legal area detection")
            return {"status": "success", "processed_count": 0}
        
        logger.info(f"Processing {total_count} decisions for legal area detection")
        
        processed_count = 0
        
        # Batch işleme
        for i in range(0, total_count, batch_size):
            batch = queryset[i:i+batch_size]
            batch_updates = []
            
            for decision in batch:
                try:
                    # Legal area tespit et
                    detected_area = legal_area_detector.get_primary_area(
                        text=decision.full_text or "",
                        title=decision.title or "",
                        summary=decision.summary or ""
                    )
                    
                    decision.detected_legal_area = detected_area
                    batch_updates.append(decision)
                    processed_count += 1
                    
                except Exception as e:
                    logger.error(f"Error detecting area for decision {decision.id}: {e}")
            
            # Batch güncelleme
            if batch_updates:
                JudicialDecision.objects.bulk_update(
                    batch_updates, 
                    ['detected_legal_area'],
                    batch_size=500
                )
                
                logger.info(f"Updated batch {i//batch_size + 1}, processed {len(batch_updates)} decisions")
        
        send_notification_email(
            subject="Hukuk Alanı Tespiti Tamamlandı",
            message=f"Toplu hukuk alanı tespiti tamamlandı. {processed_count} karar için alan tespit edildi.",
            success=True
        )
        
        return {"status": "success", "processed_count": processed_count}
        
    except Exception as e:
        logger.error(f"Bulk legal area detection failed: {e}")
        
        send_notification_email(
            subject="Hukuk Alanı Tespiti Hatası",
            message=f"Toplu hukuk alanı tespiti başarısız: {str(e)}",
            success=False
        )
        
        return {"status": "error", "message": str(e)}

@shared_task
def create_area_indexes_task():
    """Alan bazlı indexleri oluştur"""
    try:
        logger.info("Starting area-based index creation")
        
        # Management komutunu çalıştır
        call_command('manage_area_faiss', 'create_all_indexes', '--min-decisions=50')
        
        stats = area_based_faiss_manager.get_area_statistics()
        total_indexes = len(stats)
        total_decisions = sum(s['decision_count'] for s in stats.values())
        
        send_notification_email(
            subject="Alan Bazlı İndeksler Oluşturuldu",
            message=f"Alan bazlı indeksler oluşturuldu. {total_indexes} alan için toplam {total_decisions} karar indexlendi.",
            success=True
        )
        
        return {"status": "success", "total_indexes": total_indexes, "total_decisions": total_decisions}
        
    except Exception as e:
        logger.error(f"Area index creation failed: {e}")
        
        send_notification_email(
            subject="Alan Bazlı İndeks Oluşturma Hatası",
            message=f"Alan bazlı indeks oluşturma başarısız: {str(e)}",
            success=False
        )
        
        return {"status": "error", "message": str(e)}

# Resmi Gazete Task'ı
@shared_task(bind=True, max_retries=3)
def send_daily_gazette_emails(self):
    """Günlük Resmi Gazete emaillerini gönder"""
    try:
        logger.info("Starting daily gazette email task")
        
        # Management komutunu çalıştır
        call_command('send_daily_gazette')
        
        send_notification_email(
            subject="Günlük Resmi Gazete Emaili Gönderildi",
            message="Günlük Resmi Gazete özeti başarıyla tüm üyelere gönderildi.",
            success=True
        )
        
        return {"status": "success", "message": "Daily gazette emails sent"}
        
    except Exception as e:
        logger.error(f"Daily gazette email task failed: {e}")
        
        # Retry logic
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying gazette task, attempt {self.request.retries + 1}")
            raise self.retry(countdown=1800, exc=e)  # 30 dakika sonra tekrar dene
        
        # Max retry'a ulaştıysak hata emaili gönder
        send_notification_email(
            subject="Günlük Resmi Gazete Email Hatası",
            message=f"Günlük Resmi Gazete emaili gönderilemedi: {str(e)}",
            success=False
        )
        
        return {"status": "error", "message": str(e)}

# Periodic task scheduling (Celery Beat ile)
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    # Günlük Resmi Gazete Email Gönderimi
    'send-daily-gazette-emails': {
        'task': 'core.tasks.send_daily_gazette_emails',
        'schedule': crontab(hour=9, minute=0),  # Her gün sabah 09:00
    },
    
    # Legacy system (backup olarak)
    'update-faiss-index-daily': {
        'task': 'core.tasks.update_faiss_index',
        'schedule': crontab(hour=2, minute=0),  # Her gün saat 02:00
    },
    
    # Yeni alan bazlı sistem
    'update-area-indexes-daily': {
        'task': 'core.tasks.update_area_based_indexes',
        'schedule': crontab(hour=3, minute=0),  # Her gün saat 03:00 (kullanıcının isteği)
    },
    
    # Hukuk alanı tespiti (haftalık)
    'detect-legal-areas-weekly': {
        'task': 'core.tasks.detect_legal_areas_bulk',
        'schedule': crontab(day_of_week=1, hour=4, minute=0),  # Her pazartesi 04:00
        'kwargs': {'batch_size': 2000, 'max_decisions': 10000}
    },
    
    'check-index-health-hourly': {
        'task': 'core.tasks.check_index_health', 
        'schedule': crontab(minute=0),  # Her saat başı
    },
    'optimize-index-weekly': {
        'task': 'core.tasks.optimize_faiss_index',
        'schedule': crontab(day_of_week=0, hour=5, minute=0),  # Her pazar 05:00
    },
}