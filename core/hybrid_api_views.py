import json
import time
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .hybrid_faiss_search import HybridFAISSSearch
from .legal_area_detector import LegalAreaDetector
import logging

logger = logging.getLogger(__name__)

@csrf_exempt
@require_http_methods(["POST", "GET"])
def hybrid_search_api(request):
    try:
        if request.method == "POST":
            data = json.loads(request.body)
            query = data.get('query', '')
            k = data.get('k', 25)
        else:
            query = request.GET.get('q', '')
            k = int(request.GET.get('k', 25))
        
        if not query:
            return JsonResponse({'error': 'Query required'}, status=400)
        
        start_time = time.time()
        searcher = HybridFAISSSearch()
        results = searcher.smart_search(query, k)
        search_time = time.time() - start_time
        
        response_data = {
            'query': query,
            'search_time_seconds': round(search_time, 3),
            'total_results': results['total_found'],
            'primary_area': results['primary_area'],
            'detected_areas': results['detected_areas'],
            'search_stats': results['search_stats'],
            'results': results['results']
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt  
@require_http_methods(["GET"])
def system_status_api(request):
    try:
        detector = LegalAreaDetector()
        searcher = HybridFAISSSearch()
        
        test_query = "kira artış oranları"
        start_time = time.time()
        test_results = searcher.smart_search(test_query, 5)
        test_time = time.time() - start_time
        
        return JsonResponse({
            'status': 'active',
            'available_areas': len(detector.available_areas),
            'test_query': test_query,
            'test_results': test_results['total_found'],
            'test_time_seconds': round(test_time, 3),
            'primary_detected_area': test_results['primary_area']
        })
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'error': str(e)}, status=500)
