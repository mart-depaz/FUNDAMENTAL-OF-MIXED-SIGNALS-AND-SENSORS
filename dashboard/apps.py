from django.apps import AppConfig
import logging
import os
from django.conf import settings

logger = logging.getLogger(__name__)


class DashboardConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dashboard'
    verbose_name = '📚 Institutional Setup'
    
    def ready(self):
        """Initialize MQTT client when Django starts"""
        try:
            # Django dev server (StatReloader) runs app init twice; only start MQTT in the main process.
            if settings.DEBUG and os.environ.get('RUN_MAIN') != 'true':
                return

            from dashboard.mqtt_client import get_mqtt_client
            mqtt_client = get_mqtt_client()
            logger.info("[INIT] ✓ MQTT client initialized on Django startup")
        except Exception as e:
            logger.error(f"[INIT] ✗ Failed to initialize MQTT client: {e}")
            import traceback
            traceback.print_exc()
