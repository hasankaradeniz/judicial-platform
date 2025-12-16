"""
Celery configuration for judicial_platform project.
"""
import os
from celery import Celery
from django.conf import settings
from celery.schedules import crontab

# Django settings modülünü Celery için ayarla
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "judicial_platform.settings")

app = Celery("judicial_platform")

# Celery konfigürasyonu
app.config_from_object("django.conf:settings", namespace="CELERY")

# Task discovery - tüm INSTALLED_APPS'ten task'ları otomatik bul
app.autodiscover_tasks()

# Celery Beat scheduler için task tanımları
app.conf.beat_schedule = {
    # Günlük Resmi Gazete Email Gönderimi
    "send-daily-gazette-emails": {
        "task": "core.tasks.send_daily_gazette_emails",
        "schedule": crontab(hour=9, minute=0),  # Her gün sabah 09:00
        "options": {"expires": 60.0 * 60.0 * 2.0}  # 2 saat sonra expire
    },
    
    # FAISS Index Güncellemeleri - SAAT 03:00
    "update-faiss-index-daily": {
        "task": "core.tasks.update_faiss_index",
        "schedule": crontab(hour=3, minute=0),  # Her gün saat 03:00
        "options": {"expires": 60.0 * 60.0 * 2.0}  # 2 saat sonra expire
    },
    
    # Alan bazlı FAISS güncellemeleri - SAAT 03:30
    "update-area-indexes-daily": {
        "task": "core.tasks.update_area_based_indexes", 
        "schedule": crontab(hour=3, minute=30),  # Her gün saat 03:30
        "options": {"expires": 60.0 * 60.0 * 2.0}  # 2 saat sonra expire
    },
    
    # FAISS sağlık kontrolü - Her 6 saatte bir
    "check-index-health-every-6-hours": {
        "task": "core.tasks.check_index_health",
        "schedule": crontab(hour="*/6", minute=0),  # 00:00, 06:00, 12:00, 18:00
        "options": {"expires": 60.0 * 60.0}  # 1 saat sonra expire
    },
    
    # FAISS optimizasyonu - Haftalık pazar 05:00
    "optimize-index-weekly": {
        "task": "core.tasks.optimize_faiss_index",
        "schedule": crontab(day_of_week=0, hour=5, minute=0),  # Her pazar 05:00
        "options": {"expires": 60.0 * 60.0 * 4.0}  # 4 saat sonra expire
    },
    
    # Cache ısıtma - Her saatte bir
    "warm-cache-hourly": {
        "task": "core.tasks.warm_application_cache",
        "schedule": crontab(minute=0),  # Her saat başı
        "options": {"expires": 60.0 * 30.0}  # 30 dakika sonra expire
    },
    
    # Hukuk alanı tespiti - Haftalık pazartesi 04:00
    "detect-legal-areas-weekly": {
        "task": "core.tasks.detect_legal_areas_bulk",
        "schedule": crontab(day_of_week=1, hour=4, minute=0),  # Her pazartesi 04:00
        "kwargs": {"batch_size": 2000, "max_decisions": 10000},
        "options": {"expires": 60.0 * 60.0 * 4.0}  # 4 saat sonra expire
    },
}

# Timezone ayarı
app.conf.timezone = "Europe/Istanbul"

@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
