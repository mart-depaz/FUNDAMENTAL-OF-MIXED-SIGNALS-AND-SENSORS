"""
Custom middleware to disable caching in development and enable camera/microphone access
"""
from django.middleware.common import CommonMiddleware


class NoCacheCommonMiddleware(CommonMiddleware):
    """
    Custom CommonMiddleware that adds no-cache headers in development
    """
    def process_response(self, request, response):
        response = super().process_response(request, response)
        # Add no-cache headers in development
        from django.conf import settings
        if settings.DEBUG:
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            # Enable camera/microphone access from any origin in development
            response['Permissions-Policy'] = 'camera=*, microphone=*, geolocation=*'
        return response


class CameraPermissionMiddleware:
    """
    Middleware to enable camera and microphone access for local development
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Allow camera/microphone access from any origin in development
        from django.conf import settings
        if settings.DEBUG:
            # For secure contexts (HTTPS)
            response['Permissions-Policy'] = 'camera=*, microphone=*, geolocation=*'
            # Fallback for older browsers
            response['Feature-Policy'] = 'camera \'*\'; microphone \'*\'; geolocation \'*\''
            # Tell Chrome this site is trusted (suppress "Dangerous site" warning)
            response['X-Content-Type-Options'] = 'nosniff'
            response['X-Frame-Options'] = 'ALLOW-FROM *'
            response['X-XSS-Protection'] = '0'
            # Allow mixed content (for development)
            response['Upgrade-Insecure-Requests'] = '0'
        
        return response
