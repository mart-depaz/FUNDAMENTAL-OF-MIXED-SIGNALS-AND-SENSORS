from django.http import JsonResponse, HttpResponse
from django.shortcuts import render


def health_view(request):
    """Simple JSON health endpoint to verify service is live."""
    data = {
        "status": "ok",
        "host": request.get_host(),
        "scheme": request.scheme,
    }
    return JsonResponse(data)


def live_view(request):
    """Lightweight page that shows the host and provides a camera test snippet."""
    context = {
        "host": request.get_host(),
        "scheme": request.scheme,
        "full_url": f"{request.scheme}://{request.get_host()}",
    }
    return render(request, "library_root/live.html", context)
