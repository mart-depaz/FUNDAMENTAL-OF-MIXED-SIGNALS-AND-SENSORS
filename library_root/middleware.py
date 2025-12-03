"""
Custom middleware to disable caching in development
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
        return response

