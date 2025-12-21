from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # Biometric enrollment WebSocket - for individual enrollment sessions
    re_path(r'ws/biometric/enrollment/(?P<enrollment_id>\w+)/$', 
            consumers.BiometricEnrollmentConsumer.as_asgi()),
    
    # Biometric status WebSocket - for R307 status updates
    re_path(r'ws/biometric/status/$', 
            consumers.BiometricStatusConsumer.as_asgi()),
]
