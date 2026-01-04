"""
Global MQTT Client for Django
Handles all MQTT communication with ESP32 fingerprint sensor
Used by enrollment APIs and other backend processes
"""

import paho.mqtt.client as mqtt
import json
import logging
import socket
import time
import threading
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)


TOPIC_ENROLL_RESPONSE = "biometric/esp32/enroll/response"
TOPIC_FINGERPRINT_RESULT = "biometric/esp32/fingerprint"

ENROLLMENT_LOCK_KEY = "biometric_enrollment_lock"

# Global MQTT client instance
_mqtt_client = None
_mqtt_connected = False

# MQTT Configuration
MQTT_BROKER = "broker.hivemq.com"  # HiveMQ is most reliable
MQTT_PORT = 1883
MQTT_CLIENT_ID = "django_server_" + str(int(time.time()))  # Unique ID to avoid client conflicts
MQTT_KEEPALIVE = 60  # Standard keepalive
MQTT_RECONNECT_MIN = 1
MQTT_RECONNECT_MAX = 8


class MQTTClientManager:
    """Manages the global MQTT client connection and publishes"""
    
    def __init__(self):
        self.client = None
        self.is_connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 15
        self._connection_thread = None
        self._loop_started = False
        self._subscribed_topics = []  # Track subscribed topics for re-subscription on reconnect
    
    def connect_async(self):
        """Connect to MQTT broker in background thread (non-blocking)"""
        self._connection_thread = threading.Thread(target=self._connect_background, daemon=True)
        self._connection_thread.start()
        logger.info("[MQTT] Connection starting in background thread...")
    
    def _connect_background(self):
        """Connect in background without blocking"""
        try:
            try:
                resolved = socket.gethostbyname(MQTT_BROKER)
                logger.warning(f"[MQTT] Broker DNS resolved: {MQTT_BROKER} -> {resolved}")
            except Exception as e:
                logger.error(f"[MQTT] Broker DNS resolve failed for {MQTT_BROKER}: {e}")

            # Use MQTTv311 explicitly; this helps avoid some broker/protocol negotiation issues.
            # Keep the callback signatures compatible with both paho-mqtt v1 and v2.
            self.client = mqtt.Client(
                client_id=MQTT_CLIENT_ID,
                clean_session=False,  # CRITICAL: Keep subscriptions across reconnects
                userdata=self,
                protocol=mqtt.MQTTv311,
            )
            
            # Set up callbacks
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_publish = self._on_publish
            self.client.on_message = self._on_message

            # Helpful for diagnosing connection failures (DNS, broker blocked, etc.)
            self.client.on_log = self._on_log
            
            # CRITICAL: Enable automatic reconnect with exponential backoff
            self.client.reconnect_delay_set(
                min_delay=MQTT_RECONNECT_MIN, 
                max_delay=MQTT_RECONNECT_MAX
            )
            
            # Non-blocking connect; loop_start will handle the actual socket operations.
            self.client.connect_async(MQTT_BROKER, MQTT_PORT, keepalive=MQTT_KEEPALIVE)
            
            # Start network loop (non-blocking) - CRITICAL for auto-reconnect
            if not self._loop_started:
                self.client.loop_start()
                self._loop_started = True
                logger.info("[MQTT] Network loop started for auto-reconnect")
            
            # Give connection time to establish (up to 10 seconds with retries)
            max_wait = 100  # 100 * 0.1 = 10 seconds
            for i in range(max_wait):
                if self.is_connected:
                    logger.info("[MQTT] ✓ Connected to broker successfully")
                    return
                time.sleep(0.1)
            
            if not self.is_connected:
                logger.warning("[MQTT] ⚠️ Connection in progress, auto-reconnect enabled (will keep trying)")
            
        except Exception as e:
            logger.error(f"[MQTT] ✗ Failed to initialize client: {e}")
            import traceback
            traceback.print_exc()
    
    def _on_connect(self, client, userdata, flags, rc, properties=None):
        """Callback when client connects (compatible with paho-mqtt v1/v2)"""
        try:
            rc_val = int(rc)
        except Exception:
            rc_val = rc

        if rc_val == 0:
            self.is_connected = True
            self.reconnect_attempts = 0
            logger.info("[MQTT] ✓ Connected to broker - subscribing to topics...")
            
            # Re-subscribe to all topics on connection
            for topic in self._subscribed_topics:
                client.subscribe(topic, qos=1)
                logger.info(f"[MQTT] ✓ Subscribed to {topic}")
        else:
            logger.error(f"[MQTT] ✗ Connection failed with code {rc_val}")
            self.is_connected = False
    
    def _on_disconnect(self, client, userdata, rc, properties=None):
        """Callback when client disconnects (compatible with paho-mqtt v1/v2)"""
        self.is_connected = False
        try:
            rc_val = int(rc)
        except Exception:
            rc_val = rc

        if rc_val != 0:
            logger.warning(f"[MQTT] Unexpected disconnection (code {rc_val}), auto-reconnect enabled...")
        else:
            logger.info("[MQTT] Cleanly disconnected from broker")

    def _on_log(self, client, userdata, level, buf):
        """MQTT library logs (useful when broker is blocked by network/firewall)"""
        # Promote the most useful failures to WARNING/ERROR so they show up in runserver output.
        lowered = (buf or "").lower()
        if "failed" in lowered or "error" in lowered or "refused" in lowered or "name or service" in lowered or "getaddrinfo" in lowered:
            logger.warning(f"[MQTT-LOG] {buf}")
        else:
            logger.debug(f"[MQTT-LOG] {buf}")
    
    def subscribe(self, topic, qos=1):
        """Subscribe to a topic"""
        if topic not in self._subscribed_topics:
            self._subscribed_topics.append(topic)
        
        if self.client and self.is_connected:
            try:
                self.client.subscribe(topic, qos=qos)
                logger.info(f"[MQTT] ✓ Subscribed to {topic}")
                return True
            except Exception as e:
                logger.error(f"[MQTT] Failed to subscribe to {topic}: {e}")
                return False
        else:
            logger.warning(f"[MQTT] Client not connected yet, {topic} will be subscribed on reconnect")
            return False
    
    def _on_publish(self, client, userdata, mid):
        """Callback when message is published"""
        logger.debug(f"[MQTT] Message {mid} published")
    
    def _on_message(self, client, userdata, msg):
        """Callback when message is received"""
        payload_raw = msg.payload.decode(errors="replace")
        logger.debug(f"[MQTT] Received on {msg.topic}: {payload_raw}")

        try:
            payload = json.loads(payload_raw)
        except Exception:
            logger.warning(f"[MQTT] Could not parse JSON payload on {msg.topic}")
            return

        try:
            if msg.topic == TOPIC_ENROLL_RESPONSE:
                self._handle_enroll_response(payload)
            elif msg.topic == TOPIC_FINGERPRINT_RESULT:
                self._handle_fingerprint_result(payload)
        except Exception as e:
            logger.error(f"[MQTT] Error handling message on {msg.topic}: {e}")


    def _handle_fingerprint_result(self, data):
        try:
            fingerprint_id = data.get("fingerprint_id")
            confidence = data.get("confidence", 0)
            mode = (data.get("mode") or "attendance")
            match_type = data.get("match_type")
            reason = data.get("reason")

            try:
                fingerprint_id = int(fingerprint_id)
            except Exception:
                return

            mode_norm = str(mode).lower()
            if mode_norm not in {"attendance", "registration"}:
                mode_norm = "attendance"

            detections_queue_key = (
                "fingerprint_detections_queue_registration"
                if mode_norm == "registration"
                else "fingerprint_detections_queue_attendance"
            )

            logger.info(
                f"[MQTT] Fingerprint result received: mode={mode_norm} id={fingerprint_id} conf={confidence} match_type={match_type}"
            )

            detection_key = f"fingerprint_detection_{mode_norm}_{fingerprint_id}_{int(timezone.now().timestamp() * 1000)}"

            queue = cache.get(detections_queue_key, [])
            queue.append(
                {
                    "fingerprint_id": fingerprint_id,
                    "confidence": confidence,
                    "timestamp": timezone.now().isoformat(),
                    "key": detection_key,
                    "match_type": match_type,
                    "reason": reason,
                }
            )

            queue = queue[-50:]
            cache.set(detections_queue_key, queue, 60)

            logger.info(f"[MQTT] Queued fingerprint detection -> {detections_queue_key} (size={len(queue)})")
        except Exception as e:
            logger.warning(f"[MQTT] Error handling fingerprint result: {e}")


    def _handle_enroll_response(self, data):
        status = data.get("status")
        template_id = data.get("template_id")
        step = data.get("step")
        slot = data.get("slot")
        quality = data.get("quality", 0)
        message = data.get("message", "")
        success = data.get("success")

        if success is None:
            success = status in {"progress", "ready_for_confirmation", "success"}

        try:
            step = int(step) if step is not None else 0
        except Exception:
            step = 0

        progress = 0
        if status == "progress" and step:
            progress = int((step / 3) * 100)
        elif status == "ready_for_confirmation":
            progress = 100
        elif status == "success":
            progress = 100

        from dashboard.enrollment_state import find_enrollment_id_by_template_id, update_enrollment_state

        enrollment_id = find_enrollment_id_by_template_id(template_id)
        if not enrollment_id:
            logger.warning(f"[MQTT] No active enrollment found for template_id={template_id}")
            return

        # Release global lock when enrollment ends (success/error/cancelled)
        # so another student can start.
        if status in {"success", "error", "cancelled"}:
            try:
                cache.delete(ENROLLMENT_LOCK_KEY)
            except Exception:
                pass

        if status == "progress":
            update_enrollment_state(
                enrollment_id,
                current_scan=step,
                progress=progress,
                message=message,
                status="processing",
            )
        elif status == "started":
            # Clear retained enroll/request start message to prevent replay after ESP32 reconnect.
            # Clearing retained is done by publishing a zero-length payload with retain=True.
            try:
                self.publish("biometric/esp32/enroll/request", "", qos=1, retain=True)
            except Exception:
                pass

            update_enrollment_state(
                enrollment_id,
                current_scan=0,
                progress=0,
                message=message,
                status="processing",
            )
        elif status == "ready_for_confirmation":
            update_enrollment_state(
                enrollment_id,
                current_scan=3,
                progress=100,
                message=message,
                status="ready_for_confirmation",
            )
        elif status in {"capture_failed", "waiting"}:
            update_enrollment_state(
                enrollment_id,
                current_scan=step or 0,
                progress=progress,
                message=message,
                status="processing",
            )
        elif status == "success":
            update_enrollment_state(
                enrollment_id,
                current_scan=3,
                progress=100,
                message=message,
                status="completed",
                fingerprint_id=slot,
            )
        elif status in {"error", "cancelled", "blocked"}:
            update_enrollment_state(
                enrollment_id,
                progress=0,
                message=message,
                status="failed",
                error=message,
            )

        try:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync

            channel_layer = get_channel_layer()
            group_name = f"biometric_enrollment_{enrollment_id}"

            if status == "success":
                async_to_sync(channel_layer.group_send)(
                    group_name,
                    {
                        "type": "enrollment_complete",
                        "success": True,
                        "message": message or "Enrollment complete",
                        "fingerprint_id": slot,
                    },
                )
            else:
                async_to_sync(channel_layer.group_send)(
                    group_name,
                    {
                        "type": "scan_update",
                        "slot": slot or 0,
                        "step": step,
                        "success": bool(success),
                        "quality": quality,
                        "message": message,
                        "progress": progress,
                        "status": status,
                        "template_id": template_id,
                    },
                )
        except Exception as e:
            logger.warning(f"[MQTT] Could not broadcast WebSocket update: {e}")
    
    def publish(self, topic, payload, qos=1, retain=False):
        """
        Publish a message to MQTT broker with retry logic
        
        Args:
            topic: MQTT topic
            payload: Message payload (dict will be converted to JSON)
            qos: Quality of Service (0, 1, or 2)
            retain: Whether to retain the message
            
        Returns:
            bool: True if publish was successful, False otherwise
        """
        if not self.client:
            logger.error(f"[MQTT] ✗ Client not initialized, cannot publish to {topic}")
            return False
        
        # Wait for connection with exponential backoff (up to 5 seconds total)
        wait_time = 0
        max_wait = 50  # 50 * 0.1 = 5 seconds
        
        while not self.is_connected and wait_time < max_wait:
            if wait_time == 0:
                logger.warning(f"[MQTT] Client not connected to {topic}, waiting for reconnection...")
            time.sleep(0.1)
            wait_time += 1
        
        if not self.is_connected:
            logger.error(f"[MQTT] ✗ Still not connected after {wait_time/10:.1f}s, cannot publish to {topic}")
            return False
        
        try:
            # Convert dict to JSON if needed
            if isinstance(payload, dict):
                payload = json.dumps(payload)
            
            result = self.client.publish(topic, payload, qos=qos, retain=retain)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"[MQTT] ✓ Published to {topic}")
                return True
            else:
                logger.error(f"[MQTT] ✗ Publish failed with code {result.rc}")
                return False
        except Exception as e:
            logger.error(f"[MQTT] ✗ Error publishing to {topic}: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from broker"""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            logger.info("[MQTT] Disconnected")


# Global instance
def get_mqtt_client():
    """Get or create the global MQTT client"""
    global _mqtt_client
    
    if _mqtt_client is None:
        _mqtt_client = MQTTClientManager()
        _mqtt_client.connect_async()  # Non-blocking connection

        _mqtt_client.subscribe(TOPIC_ENROLL_RESPONSE, qos=1)
        _mqtt_client.subscribe(TOPIC_FINGERPRINT_RESULT, qos=1)
    
    return _mqtt_client
