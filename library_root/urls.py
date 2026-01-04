# library_system/library_root/urls.py



from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.urls import re_path
from library_root import status_views
from dashboard import views as dashboard_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('accounts.urls')),  # For login/signup
    path('dashboard/', include('dashboard.urls')),  # Include dashboard URLs with namespace
    # API routes without /dashboard/ prefix for biometric detection
    path('api/instructor/attendance/start/', dashboard_views.instructor_start_biometric_detection_view, name='api_instructor_start_biometric_detection'),
    path('api/instructor/attendance/stop/', dashboard_views.instructor_stop_biometric_detection_view, name='api_instructor_stop_biometric_detection'),
    # Health and live checks
    path('health/', status_views.health_view, name='health'),
    path('live/', status_views.live_view, name='live'),
]

# Serve media files during development with no-cache headers
if settings.DEBUG:
    from django.views.static import serve
    from django.urls import re_path
    
    # Custom serve function with no-cache headers
    def serve_media_no_cache(request, path, document_root=None, show_indexes=False):
        response = serve(request, path, document_root, show_indexes)
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response
    
    urlpatterns += [
        re_path(r'^%s(?P<path>.*)$' % settings.MEDIA_URL.lstrip('/'), serve_media_no_cache, {'document_root': settings.MEDIA_ROOT}),
    ]

# Also allow direct health path for environments where include ordering matters
urlpatterns += [
    re_path(r'^health/?$', status_views.health_view),
]