from django.apps import AppConfig
import threading
import os

# Thread-safe lock for MQTT bridge initialization
_mqtt_init_lock = threading.Lock()
_mqtt_initialized = False


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'
    verbose_name = '👥 User Management'
    
    def ready(self):
        """MQTT bridge is now embedded in Django's enrollment views"""
        # MQTT communication is handled internally by enrollment state management
        # No separate bridge initialization needed
        pass
