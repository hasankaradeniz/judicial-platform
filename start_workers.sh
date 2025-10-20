#!/bin/bash

# FAISS Otomatik Sistemini Başlatma Scripti
# Kullanım: ./start_workers.sh

echo "🚀 FAISS Otomatik Sistemi Başlatılıyor..."

# Redis'in çalışıp çalışmadığını kontrol et
if ! redis-cli ping > /dev/null 2>&1; then
    echo "❌ Redis çalışmıyor! Lütfen Redis'i başlatın:"
    echo "   sudo systemctl start redis-server"
    exit 1
fi

echo "✅ Redis bağlantısı OK"

# Gerekli dizinleri oluştur
mkdir -p faiss_dizinleri
mkdir -p logs

# Celery worker'ları arka planda başlat
echo "🔧 Celery worker'ları başlatılıyor..."

# FAISS worker
nohup source venv/bin/activate && celery -A judicial_platform worker -Q faiss --loglevel=info \
    --logfile=logs/faiss_worker.log > /dev/null 2>&1 &
FAISS_PID=$!

# Monitoring worker  
nohup source venv/bin/activate && celery -A judicial_platform worker -Q monitoring --loglevel=info \
    --logfile=logs/monitoring_worker.log > /dev/null 2>&1 &
MONITORING_PID=$!

# Cache worker
nohup source venv/bin/activate && celery -A judicial_platform worker -Q cache --loglevel=info \
    --logfile=logs/cache_worker.log > /dev/null 2>&1 &
CACHE_PID=$!

# Celery Beat (scheduler)
nohup source venv/bin/activate && celery -A judicial_platform beat --loglevel=info \
    --logfile=logs/celery_beat.log > /dev/null 2>&1 &
BEAT_PID=$!

# PID'leri kaydet
echo $FAISS_PID > logs/faiss_worker.pid
echo $MONITORING_PID > logs/monitoring_worker.pid  
echo $CACHE_PID > logs/cache_worker.pid
echo $BEAT_PID > logs/celery_beat.pid

echo "✅ Tüm worker'lar başlatıldı!"
echo ""
echo "📋 Process ID'ler:"
echo "   FAISS Worker: $FAISS_PID"
echo "   Monitoring Worker: $MONITORING_PID" 
echo "   Cache Worker: $CACHE_PID"
echo "   Celery Beat: $BEAT_PID"
echo ""
echo "📁 Log dosyaları:"
echo "   tail -f logs/faiss_worker.log"
echo "   tail -f logs/monitoring_worker.log"
echo "   tail -f logs/cache_worker.log" 
echo "   tail -f logs/celery_beat.log"
echo ""
echo "🏥 FAISS durumunu kontrol et:"
echo "   source venv/bin/activate && python manage.py manage_faiss status"
echo ""
echo "🛑 Sistemı durdurmak için:"
echo "   ./stop_workers.sh"

# İlk FAISS kontrolünü yap
echo "🔍 İlk FAISS durumu kontrol ediliyor..."
source venv/bin/activate && python manage.py manage_faiss status