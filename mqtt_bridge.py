"""
Django MQTT Bridge - Connects Django to ESP32 via MQTT Broker
Allows students to register fingerprints from any network
"""

import paho.mqtt.client as mqtt
import json
import logging
from django.core.management.base import BaseCommand
from accounts.models import BiometricData
from django.utils import timezone

logger = logging.getLogger(__name__)

# MQTT Configuration
MQTT_BROKER = "broker.hivemq.com"  # Free public MQTT broker
MQTT_PORT = 1883
MQTT_CLIENT_ID = "django_biometric_server"
MQTT_KEEPALIVE = 60

# MQTT Topics
TOPIC_ENROLL_REQUEST = "biometric/esp32/enroll/request"
TOPIC_ENROLL_RESPONSE = "biometric/esp32/enroll/response"
TOPIC_DETECT_REQUEST = "biometric/esp32/detect/request"
TOPIC_DETECT_RESPONSE = "biometric/esp32/detect/response"
TOPIC_STATUS = "biometric/esp32/status"
TOPIC_FINGERPRINT_RESULT = "biometric/esp32/fingerprint"
TOPIC_COMMAND = "biometric/esp32/command"


class MQTTBridge:
    """MQTT Bridge for bidirectional communication with ESP32"""
    
    def __init__(self):
        self.client = mqtt.Client(client_id=MQTT_CLIENT_ID)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        self.is_connected = False
        
    def on_connect(self, client, userdata, flags, rc):
        """Callback when client connects to MQTT broker"""
        if rc == 0:
            logger.info("✓ Connected to MQTT Broker")
            self.is_connected = True
            
            # Subscribe to topics
            client.subscribe(TOPIC_ENROLL_RESPONSE)
            client.subscribe(TOPIC_DETECT_RESPONSE)
            client.subscribe(TOPIC_STATUS)
            client.subscribe(TOPIC_FINGERPRINT_RESULT)
            
            logger.info("Subscribed to response topics")
        else:
            logger.error(f"✗ MQTT Connection failed with code: {rc}")
            self.is_connected = False
    
    def on_disconnect(self, client, userdata, rc):
        """Callback when client disconnects"""
        self.is_connected = False
        if rc != 0:
            logger.warning(f"Unexpected disconnection (code: {rc})")
    
    def on_message(self, client, userdata, msg):
        """Callback when message is received"""
        topic = msg.topic
        payload = msg.payload.decode()
        
        logger.info(f"Message received: {topic} -> {payload}")
        
        try:
            data = json.loads(payload)
            
            if topic == TOPIC_ENROLL_RESPONSE:
                self.handle_enrollment_response(data)
            elif topic == TOPIC_FINGERPRINT_RESULT:
                self.handle_fingerprint_detection(data)
            elif topic == TOPIC_STATUS:
                self.handle_device_status(data)
                
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON payload: {payload}")
    
    def connect(self):
        """Connect to MQTT broker"""
        try:
            logger.info(f"Connecting to MQTT broker: {MQTT_BROKER}:{MQTT_PORT}")
            self.client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE)
            self.client.loop_start()
            logger.info("MQTT client loop started")
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
    
    def disconnect(self):
        """Disconnect from MQTT broker"""
        self.client.loop_stop()
        self.client.disconnect()
        logger.info("Disconnected from MQTT broker")
    
    def request_enrollment(self, slot, student_id, template_id):
        """Request ESP32 to start fingerprint enrollment"""
        payload = {
            "slot": slot,
            "student_id": student_id,
            "template_id": template_id,
            "action": "start"
        }
        self.publish(TOPIC_ENROLL_REQUEST, json.dumps(payload))
        logger.info(f"Enrollment requested: slot={slot}, template_id={template_id}")
    
    def cancel_enrollment(self, slot):
        """Request ESP32 to cancel ongoing enrollment"""
        payload = {
            "slot": slot,
            "action": "cancel"
        }
        self.publish(TOPIC_ENROLL_REQUEST, json.dumps(payload))
        logger.info(f"Enrollment cancelled: slot={slot}")
    
    def enable_detection(self, mode="attendance"):
        """Enable fingerprint detection on ESP32"""
        payload = {
            "action": "enable",
            "mode": mode  # "attendance" or "registration"
        }
        self.publish(TOPIC_DETECT_REQUEST, json.dumps(payload))
        logger.info(f"Detection enabled: mode={mode}")
    
    def disable_detection(self):
        """Disable fingerprint detection on ESP32"""
        payload = {
            "action": "disable"
        }
        self.publish(TOPIC_DETECT_REQUEST, json.dumps(payload))
        logger.info("Detection disabled")
    
    def send_command(self, command, **kwargs):
        """Send general command to ESP32"""
        payload = {"command": command}
        payload.update(kwargs)
        self.publish(TOPIC_COMMAND, json.dumps(payload))
        logger.info(f"Command sent: {command}")
    
    def publish(self, topic, payload):
        """Publish message to MQTT topic"""
        if self.is_connected:
            result = self.client.publish(topic, payload)
            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                logger.error(f"Failed to publish to {topic}: {result.rc}")
        else:
            logger.warning(f"MQTT not connected. Cannot publish to {topic}")
    
    def handle_enrollment_response(self, data):
        """Handle enrollment response from ESP32 - Update enrollment state and database"""
        status = data.get("status")
        slot = data.get("slot")
        step = data.get("step")
        template_id = data.get("template_id")
        message = data.get("message")
        success = data.get("success", True)
        quality = data.get("quality")
        
        logger.info(f"[MQTT] Enrollment response: status={status}, step={step}, template_id={template_id}")
        
        # Import here to avoid circular imports
        from dashboard.views_enrollment_apis import _enrollment_states
        from django.utils import timezone
        
        # Extract student_id from template_id (format: UUID or student_<student_id>)
        student_id = None
        enrollment_id = None
        
        # Try to find matching enrollment by template_id (most reliable way)
        for enroll_id, state in list(_enrollment_states.items()):
            if state.get('template_id') == template_id:
                enrollment_id = enroll_id
                logger.info(f"[MQTT] ✓ Matched enrollment by template_id: {enrollment_id}")
                break
        
        # Fallback: If no exact match found, use most recent enrollment
        # This handles race condition where enrollment might be created after MQTT message arrives
        if not enrollment_id:
            logger.warning(f"[MQTT] ⚠ No exact template_id match for {template_id}")
            logger.info(f"[MQTT] Available enrollments: {list(_enrollment_states.keys())}")
            
            # Get the most recent enrollment that's still processing
            most_recent = None
            most_recent_time = None
            for enroll_id, state in list(_enrollment_states.items()):
                if state.get('status') == 'processing' or state.get('status') == 'ready_for_confirmation':
                    created_at = state.get('created_at')
                    if created_at:
                        try:
                            import dateutil.parser
                            created_time = dateutil.parser.parse(created_at)
                            if most_recent_time is None or created_time > most_recent_time:
                                most_recent = enroll_id
                                most_recent_time = created_time
                        except:
                            # Fallback: just use first processing enrollment
                            if most_recent is None:
                                most_recent = enroll_id
            
            if most_recent:
                enrollment_id = most_recent
                logger.warning(f"[MQTT] ⚠ Using most recent enrollment as fallback: {enrollment_id}")
                # Update the template_id in the state so future messages match correctly
                _enrollment_states[enrollment_id]['template_id'] = template_id
        
        if enrollment_id and enrollment_id in _enrollment_states:
            state = _enrollment_states[enrollment_id]
            logger.info(f"[MQTT] ✓ Updating enrollment {enrollment_id}: status={status}, step={step}")
            
            if status == "progress":
                # Update progress for current scan
                logger.info(f"[MQTT] ✓ SCAN {step}/3 progress received")
                state['status'] = 'processing'
                state['current_scan'] = step
                state['progress'] = (step / 3) * 100  # Calculate progress percentage
                state['message'] = message
                state['last_scan_quality'] = quality
                state['success'] = success
                state['fingerprint_slot'] = slot
                state['template_id'] = template_id  # Always update with actual template_id from ESP32
                
                # Add to scans list if not already there
                existing_scans = [s['step'] for s in state.get('scans', [])]
                if step not in existing_scans:
                    state['scans'].append({
                        'step': step,
                        'message': message,
                        'quality': quality,
                        'timestamp': timezone.now().isoformat()
                    })
                    logger.info(f"[MQTT] ✓ Added scan {step} to history. Total scans: {len(state['scans'])}")
                else:
                    logger.info(f"[MQTT] ⓘ Scan {step} already recorded")
                
            elif status == "ready_for_confirmation":
                # All scans complete, waiting for user confirmation
                logger.info(f"[MQTT] ✓ All scans ready - awaiting user confirmation")
                state['status'] = 'ready_for_confirmation'
                state['current_scan'] = 3
                state['progress'] = 100
                state['message'] = message
                state['fingerprint_slot'] = slot
                state['template_id'] = template_id
                
            elif status == "capture_failed":
                # Low quality scan, user needs to retry
                logger.warning(f"[MQTT] ⚠ Scan {step} REJECTED - quality too low")
                state['status'] = 'processing'
                state['message'] = f"Scan {step} rejected: {message}"
                state['last_scan_quality'] = quality
                state['capture_failed'] = True
                state['current_scan'] = step - 1  # Go back to previous scan
                state['progress'] = ((step - 1) / 3) * 100
                
            elif status == "success":
                # Model successfully created and stored
                logger.info(f"[MQTT] ✓ Fingerprint model stored in slot {slot}")
                state['status'] = 'completed'
                state['current_scan'] = 3
                state['progress'] = 100
                state['message'] = message
                state['fingerprint_id'] = slot  # Store the slot number as fingerprint ID
                state['fingerprint_slot'] = slot
                state['template_id'] = template_id
                
                # Update database
                try:
                    from accounts.models import BiometricData
                    biometric = BiometricData.objects.get(
                        fingerprint_template_id=template_id
                    )
                    biometric.is_enrolled = True
                    biometric.slot_number = slot
                    biometric.enrolled_at = timezone.now()
                    biometric.save()
                    logger.info(f"[MQTT] ✓ Database updated: fingerprint {template_id} -> slot {slot}")
                except Exception as e:
                    logger.warning(f"[MQTT] ⚠ Could not update database: {e}")
                    
            elif status == "error":
                # Enrollment failed
                logger.error(f"[MQTT] ✗ Enrollment error: {message}")
                state['status'] = 'failed'
                state['message'] = message
                state['error'] = message
        else:
            logger.error(f"[MQTT] ✗ CRITICAL: No matching enrollment found!")
            logger.error(f"[MQTT] template_id={template_id}, enrollment_id={enrollment_id}")
            logger.error(f"[MQTT] Available states: {list(_enrollment_states.keys())}")
    
    def handle_fingerprint_detection(self, data):
        """Handle fingerprint detection from ESP32"""
        fingerprint_id = data.get("fingerprint_id")
        confidence = data.get("confidence")
        mode = data.get("mode")
        
        logger.info(f"Fingerprint detected: ID={fingerprint_id}, "
                   f"confidence={confidence}, mode={mode}")
        
        # Process detection (update attendance, etc.)
        # This will be handled by your existing logic
    
    def handle_device_status(self, data):
        """Handle device status updates"""
        device_id = data.get("device_id")
        status = data.get("status")
        fingerprints_stored = data.get("fingerprints_stored")
        
        logger.info(f"Device status: {device_id} -> {status} "
                   f"(fingerprints: {fingerprints_stored})")


# Global MQTT bridge instance
mqtt_bridge = None


def get_mqtt_bridge():
    """Get or create MQTT bridge instance"""
    global mqtt_bridge
    if mqtt_bridge is None:
        mqtt_bridge = MQTTBridge()
        mqtt_bridge.connect()
    return mqtt_bridge


class Command(BaseCommand):
    """Django management command to run MQTT bridge"""
    help = 'Start MQTT bridge for ESP32-Django communication'
    
    def handle(self, *args, **options):
        bridge = get_mqtt_bridge()
        self.stdout.write(self.style.SUCCESS('✓ MQTT Bridge started'))
        self.stdout.write(f'Broker: {MQTT_BROKER}:{MQTT_PORT}')
        
        try:
            # Keep the bridge running
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('Shutting down...'))
            bridge.disconnect()
