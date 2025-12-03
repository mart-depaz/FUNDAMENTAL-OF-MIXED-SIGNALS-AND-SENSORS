# library_system/library_root/urls.py



from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('accounts.urls')),  # For login/signup
    path('dashboard/', include('dashboard.urls')),  # Include dashboard URLs with namespace
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