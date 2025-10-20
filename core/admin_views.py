# core/admin_views.py

from django.shortcuts import render, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.files.storage import default_storage
from core.admin_pdf_processor import PDFProcessor
from core.models import MevzuatGelismis, MevzuatTuru
import json

@staff_member_required
def admin_pdf_upload(request):
    """Admin PDF upload sayfası"""
    if request.method == 'POST':
        return handle_pdf_upload(request)
    
    # İstatistikleri al
    stats = {
        'total_mevzuat': MevzuatGelismis.objects.count(),
        'by_type': {}
    }
    
    for mevzuat_type in MevzuatTuru.objects.all():
        count = MevzuatGelismis.objects.filter(mevzuat_turu=mevzuat_type).count()
        stats['by_type'][mevzuat_type.ad] = count
    
    context = {
        'stats': stats,
        'mevzuat_types': [
            ('kanun', 'Kanun'),
            ('yonetmelik', 'Yönetmelik'),
            ('kararname', 'Kararname'),
            ('tuzuk', 'Tüzük'),
            ('teblig', 'Tebliğ')
        ]
    }
    
    return render(request, 'admin/pdf_upload.html', context)

@staff_member_required
def handle_pdf_upload(request):
    """PDF upload işlemini handle et"""
    try:
        pdf_files = request.FILES.getlist('pdf_files')
        mevzuat_type = request.POST.get('mevzuat_type', 'kanun')
        
        if not pdf_files:
            messages.error(request, 'Lütfen en az bir PDF dosyası seçin.')
            return redirect('admin_pdf_upload')
        
        processor = PDFProcessor()
        
        for pdf_file in pdf_files:
            # Dosya validasyonu
            if not pdf_file.name.lower().endswith('.pdf'):
                messages.warning(request, f'{pdf_file.name} PDF dosyası değil, atlandı.')
                continue
            
            if pdf_file.size > 50 * 1024 * 1024:  # 50MB limit
                messages.warning(request, f'{pdf_file.name} çok büyük (>50MB), atlandı.')
                continue
            
            try:
                # PDF'i işle
                mevzuat = processor.process_pdf_file(pdf_file, mevzuat_type, request.user)
                messages.success(request, f'✅ {mevzuat.baslik} başarıyla kaydedildi.')
                
            except Exception as e:
                messages.error(request, f'❌ {pdf_file.name}: {str(e)}')
        
        # İstatistikleri göster
        stats = processor.get_stats()
        if stats['saved'] > 0:
            messages.info(request, f"📊 {stats['processed']} PDF işlendi, {stats['saved']} mevzuat kaydedildi.")
        
        return redirect('admin_pdf_upload')
        
    except Exception as e:
        messages.error(request, f'Genel hata: {str(e)}')
        return redirect('admin_pdf_upload')

@staff_member_required
@csrf_exempt
@require_http_methods(["POST"])
def ajax_pdf_upload(request):
    """Ajax ile PDF upload"""
    try:
        pdf_file = request.FILES.get('pdf_file')
        mevzuat_type = request.POST.get('mevzuat_type', 'kanun')
        
        if not pdf_file:
            return JsonResponse({'success': False, 'error': 'PDF dosyası seçilmedi'})
        
        if not pdf_file.name.lower().endswith('.pdf'):
            return JsonResponse({'success': False, 'error': 'Sadece PDF dosyaları kabul edilir'})
        
        if pdf_file.size > 50 * 1024 * 1024:
            return JsonResponse({'success': False, 'error': 'Dosya çok büyük (max 50MB)'})
        
        processor = PDFProcessor()
        mevzuat = processor.process_pdf_file(pdf_file, mevzuat_type, request.user)
        
        return JsonResponse({
            'success': True,
            'mevzuat': {
                'id': mevzuat.id,
                'title': mevzuat.baslik,
                'number': mevzuat.mevzuat_numarasi,
                'type': mevzuat.mevzuat_turu.ad if mevzuat.mevzuat_turu else '',
                'url': f'/legislation/{mevzuat.id}/'
            },
            'stats': processor.get_stats()
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@staff_member_required
def admin_mevzuat_list(request):
    """Admin mevzuat listesi"""
    mevzuat_list = MevzuatGelismis.objects.select_related(
        'mevzuat_turu', 'kategori'
    ).order_by('-kayit_tarihi')[:100]
    
    context = {
        'mevzuat_list': mevzuat_list,
        'total_count': MevzuatGelismis.objects.count()
    }
    
    return render(request, 'admin/mevzuat_list.html', context)

@staff_member_required
@require_http_methods(["POST"])
def admin_delete_mevzuat(request, mevzuat_id):
    """Mevzuat sil"""
    try:
        mevzuat = MevzuatGelismis.objects.get(id=mevzuat_id)
        title = mevzuat.baslik
        
        # PDF dosyasını da sil
        if mevzuat.kaynak_url:
            try:
                default_storage.delete(mevzuat.kaynak_url)
            except:
                pass
        
        mevzuat.delete()
        
        messages.success(request, f'✅ {title} başarıyla silindi.')
        
    except MevzuatGelismis.DoesNotExist:
        messages.error(request, 'Mevzuat bulunamadı.')
    except Exception as e:
        messages.error(request, f'Silme hatası: {str(e)}')
    
    return redirect('admin_mevzuat_list')