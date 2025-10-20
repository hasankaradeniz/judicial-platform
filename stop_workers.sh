#!/bin/bash

# FAISS Otomatik Sistemini Durdurma Scripti
# Kullanım: ./stop_workers.sh

echo "🛑 FAISS Otomatik Sistemi Durduruluyor..."

# PID dosyalarını kontrol et ve process'leri durdur
if [ -f logs/faiss_worker.pid ]; then
    FAISS_PID=$(cat logs/faiss_worker.pid)
    if kill -0 $FAISS_PID 2>/dev/null; then
        kill $FAISS_PID
        echo "✅ FAISS Worker durduruldu (PID: $FAISS_PID)"
    fi
    rm logs/faiss_worker.pid
fi

if [ -f logs/monitoring_worker.pid ]; then
    MONITORING_PID=$(cat logs/monitoring_worker.pid)
    if kill -0 $MONITORING_PID 2>/dev/null; then
        kill $MONITORING_PID
        echo "✅ Monitoring Worker durduruldu (PID: $MONITORING_PID)"
    fi
    rm logs/monitoring_worker.pid
fi

if [ -f logs/cache_worker.pid ]; then
    CACHE_PID=$(cat logs/cache_worker.pid)
    if kill -0 $CACHE_PID 2>/dev/null; then
        kill $CACHE_PID
        echo "✅ Cache Worker durduruldu (PID: $CACHE_PID)"
    fi
    rm logs/cache_worker.pid
fi

if [ -f logs/celery_beat.pid ]; then
    BEAT_PID=$(cat logs/celery_beat.pid)
    if kill -0 $BEAT_PID 2>/dev/null; then
        kill $BEAT_PID
        echo "✅ Celery Beat durduruldu (PID: $BEAT_PID)"
    fi
    rm logs/celery_beat.pid
fi

# Celery process'lerini tamamen temizle
pkill -f "celery.*judicial_platform" 2>/dev/null

echo ""
echo "✅ Tüm worker'lar durduruldu!"
echo ""
echo "📊 Sistem durumu:"
echo "   ps aux | grep celery | grep -v grep"