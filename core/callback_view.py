from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import logging

logger = logging.getLogger(__name__)

@csrf_exempt
@require_POST
def payment_callback(request):
    """Param Modal Payment callback"""
    try:
        # Log all POST data
        logger.info(f"Payment callback received: {request.POST}")
        
        # Basic response to Param
        return JsonResponse({"status": "received"})
        
    except Exception as e:
        logger.error(f"Callback error: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)
