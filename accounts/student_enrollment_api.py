"""
API views for student fingerprint enrollment and attendance
Works with MQTT - students can use any network (mobile data, different WiFi, etc.)
"""

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json
import uuid
import time
import logging
from accounts.models import CustomUser
from dashboard.models import BiometricRegistration, Course
from dashboard.mqtt_client import get_mqtt_client
from django.utils import timezone
from django.core.cache import cache
from django.db.models import Max
from threading import Lock

logger = logging.getLogger(__name__)

ENROLLMENT_LOCK_KEY = "biometric_enrollment_lock"
ENROLLMENT_LOCK_TTL_SECONDS = 5 * 60

# Global dictionaries to track enrollment mappings
# template_id -> enrollment_id (for WebSocket routing)
enrollment_id_map = {}
# slot -> template_id (for finding template_id in progress/error messages that don't include it)
slot_to_template_map = {}
enrollment_id_lock = Lock()


def get_enrollment_id(template_id=None, slot=None):
    """
    Get enrollment_id from template_id or slot number
    Progress/error messages might not have template_id, so we need both lookups
    """
    with enrollment_id_lock:
        # Try template_id first (for messages that include it)
        if template_id and template_id in enrollment_id_map:
            return enrollment_id_map[template_id]
        
        # Try slot lookup (for messages that don't include template_id)
        if slot and slot in slot_to_template_map:
            template_id_mapped = slot_to_template_map[slot]
            if template_id_mapped in enrollment_id_map:
                return enrollment_id_map[template_id_mapped]
    
    return None


def get_enrollment_id_for_template(template_id):
    """Look up the enrollment_id (WebSocket ID) from template_id"""
    with enrollment_id_lock:
        enrollment_id = enrollment_id_map.get(template_id)
    return enrollment_id

@csrf_exempt
@require_http_methods(["POST"])
def start_fingerprint_enrollment(request):
    """
    Student starts fingerprint enrollment
    Works from any network (mobile, different WiFi, etc.)
    
    POST /accounts/api/student/enroll/start/
    {
        "student_id": "STU001",
        "enrollment_id": "enrollment_1234567890_abc123",
        "template_id": "template_1234567890_abc123",
        "course_id": 1
    }
    """
    try:
        from dashboard.enrollment_state import create_enrollment_state, cleanup_old_enrollments, get_all_states
        
        data = json.loads(request.body)
        student_id = data.get('student_id')
        enrollment_id = data.get('enrollment_id')  # Frontend-generated ID for WebSocket routing
        template_id = data.get('template_id')  # Frontend-generated ID for ESP32 to send back
        course_id = data.get('course_id', 1)
        
        if not student_id:
            return JsonResponse({
                'status': 'error',
                'message': 'student_id required'
            }, status=400)
        
        if not enrollment_id:
            return JsonResponse({
                'status': 'error',
                'message': 'enrollment_id required'
            }, status=400)
        
        if not template_id:
            return JsonResponse({
                'status': 'error',
                'message': 'template_id required'
            }, status=400)
        
        # Get student by school_id
        try:
            student = CustomUser.objects.get(school_id=student_id, is_student=True)
        except CustomUser.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': f'Student with ID {student_id} not found'
            }, status=404)
        
        # Global lock: allow only ONE active enrollment at a time to avoid slot conflicts.
        lock_payload = {
            'student_id': student.school_id,
            'student_user_id': student.id,
            'template_id': template_id,
            'enrollment_id': enrollment_id,
            'created_at': timezone.now().isoformat(),
        }

        lock_acquired = cache.add(ENROLLMENT_LOCK_KEY, lock_payload, timeout=ENROLLMENT_LOCK_TTL_SECONDS)
        if not lock_acquired:
            existing_lock = cache.get(ENROLLMENT_LOCK_KEY)
            try:
                if existing_lock and existing_lock.get('student_user_id') == student.id:
                    cache.set(ENROLLMENT_LOCK_KEY, lock_payload, timeout=ENROLLMENT_LOCK_TTL_SECONDS)
                else:
                    locked_by = (existing_lock or {}).get('student_id') or 'another student'
                    return JsonResponse({
                        'status': 'blocked',
                        'message': f'Another student is currently enrolling ({locked_by}). Please wait...'
                    }, status=409)
            except Exception:
                return JsonResponse({
                    'status': 'blocked',
                    'message': 'Another student is currently enrolling. Please wait...'
                }, status=409)

        # Get course by id
        try:
            course = Course.objects.get(id=course_id, is_active=True, deleted_at__isnull=True, is_archived=False)
        except Course.DoesNotExist:
            cache.delete(ENROLLMENT_LOCK_KEY)
            return JsonResponse({
                'status': 'error',
                'message': 'Course not found'
            }, status=404)
        
        # Check if already enrolled for this course
        existing = BiometricRegistration.objects.filter(
            student=student,
            course=course,
            is_active=True
        ).first()
        
        # CRITICAL FIX: Clean up old enrollments from previous attempts
        # This prevents state collision when re-registering
        print(f"[API] Cleaning up old enrollments for user {student.id}, course {course_id}...")
        cleanup_old_enrollments(student.id, course_id)
        
        # Allow re-enrollment: if already enrolled, we'll update with a new fingerprint
        # This lets students re-register if they want to update their fingerprint
        old_slot = None
        if existing and existing.fingerprint_id:
            old_slot = existing.fingerprint_id
            print(f"[ENROLLMENT] Student {student_id} is re-enrolling. Old slot: {old_slot}")
        
        # Allocate fingerprint slot in reserved range >= 100 to avoid collisions with legacy IDs.
        available_slot = None
        try:
            if old_slot is not None and int(old_slot) >= 100:
                available_slot = int(old_slot)
        except Exception:
            available_slot = None

        if available_slot is None:
            existing_student_slot = BiometricRegistration.objects.filter(
                student=student,
                is_active=True,
                fingerprint_id__gte=100,
            ).order_by('-created_at').values_list('fingerprint_id', flat=True).first()
            try:
                if existing_student_slot is not None and int(existing_student_slot) >= 100:
                    available_slot = int(existing_student_slot)
            except Exception:
                available_slot = None

        if available_slot is None:
            max_existing_slot = BiometricRegistration.objects.aggregate(max_id=Max('fingerprint_id'))['max_id'] or 99
            try:
                max_existing_slot = int(max_existing_slot)
            except Exception:
                max_existing_slot = 99
            available_slot = max(100, max_existing_slot + 1)

        # Ensure we don't exceed sensor capacity (R307 typically supports 300 templates)
        if available_slot and int(available_slot) > 300:
            try:
                cache.delete(ENROLLMENT_LOCK_KEY)
            except Exception:
                pass
            return JsonResponse({
                'status': 'error',
                'message': 'No available fingerprint slots (sensor capacity reached).'
            }, status=400)
        
        # Create or update biometric registration
        biometric, created = BiometricRegistration.objects.update_or_create(
            student=student,
            course=course,
            defaults={
                'fingerprint_id': available_slot,
                'is_active': True,
                'biometric_type': 'fingerprint'
            }
        )
        
        # CRITICAL FIX: Use centralized enrollment state instead of old mapping
        logger.info(f"[API] Creating enrollment in centralized state...")
        logger.info(f"[API]   enrollment_id: {enrollment_id}")
        logger.info(f"[API]   template_id: {template_id}")
        logger.info(f"[API]   slot: {available_slot}")
        
        create_enrollment_state(
            enrollment_id=enrollment_id,
            user_id=student.id,
            course_id=course_id,
            template_id=template_id,  # Store the template_id from frontend
            is_re_registration=existing is not None,
            old_fingerprint_id=existing.fingerprint_id if existing else None
        )

        try:
            from dashboard.enrollment_state import _enrollment_states
            if enrollment_id in _enrollment_states:
                _enrollment_states[enrollment_id]['fingerprint_slot'] = available_slot
        except Exception:
            pass
        
        logger.info(f"[API] Enrollment created in centralized state with template_id={template_id}")
        
        # ==================== SEND ENROLLMENT REQUEST TO ESP32 VIA MQTT ====================
        # This tells the ESP32 to start waiting for 3 finger scans
        mqtt_client = get_mqtt_client()
        
        logger.info(f"[API] ===== SENDING MQTT ENROLLMENT REQUEST =====")
        logger.info(f"[API] MQTT client exists: {mqtt_client is not None}")
        logger.info(f"[API] MQTT is_connected: {mqtt_client.is_connected if mqtt_client else 'N/A'}")
        
        if not mqtt_client or not mqtt_client.is_connected:
            try:
                from dashboard.enrollment_state import delete_enrollment_state
                delete_enrollment_state(enrollment_id)
            except Exception:
                pass

            try:
                current_lock = cache.get(ENROLLMENT_LOCK_KEY)
                if current_lock and current_lock.get('student_user_id') == student.id:
                    cache.delete(ENROLLMENT_LOCK_KEY)
            except Exception:
                pass

            return JsonResponse(
                {
                    "status": "error",
                    "message": "MQTT broker not connected. Please wait a moment and try again.",
                },
                status=503,
            )

        if mqtt_client and mqtt_client.is_connected:
            enrollment_request = {
                'action': 'start',
                'template_id': template_id,
                'slot': available_slot,
                'scans_required': 3
            }
            
            topic = 'biometric/esp32/enroll/request'
            logger.info(f"[API] Publishing to topic: {topic}")
            logger.info(f"[API] Payload: {enrollment_request}")
            
            # Use retain=True so if ESP32 briefly disconnects (common on weak WiFi),
            # it will still receive the latest start command immediately on reconnect.
            success = mqtt_client.publish(topic, enrollment_request, qos=1, retain=True)
            
            logger.info(f"[API] MQTT publish result: {success}")
            if success:
                logger.info(f"[API] Sent enrollment request to ESP32")
                logger.info(f"[API]   Template ID: {template_id}")
                logger.info(f"[API]   Slot: {available_slot}")
            else:
                logger.warning(f"[API] Failed to publish enrollment request to ESP32")
                try:
                    from dashboard.enrollment_state import delete_enrollment_state
                    delete_enrollment_state(enrollment_id)
                except Exception:
                    pass

                try:
                    current_lock = cache.get(ENROLLMENT_LOCK_KEY)
                    if current_lock and current_lock.get('student_user_id') == student.id:
                        cache.delete(ENROLLMENT_LOCK_KEY)
                except Exception:
                    pass

                return JsonResponse(
                    {
                        "status": "error",
                        "message": "Failed to send enrollment request to ESP32. Please try again.",
                    },
                    status=502,
                )
        
        return JsonResponse({
            'status': 'success',
            'message': 'Enrollment started',
            'enrollment_id': enrollment_id,
            'template_id': template_id,
            'slot': available_slot,
            'next_step': 'Place your finger on the sensor 3 times'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid JSON'
        }, status=400)
    except Exception as e:
        import traceback
        traceback.print_exc()
        try:
            # best-effort lock cleanup if we acquired it
            current_lock = cache.get(ENROLLMENT_LOCK_KEY)
            if current_lock and current_lock.get('template_id') == data.get('template_id'):
                cache.delete(ENROLLMENT_LOCK_KEY)
        except Exception:
            pass
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def cancel_fingerprint_enrollment(request):
    """
    Cancel ongoing fingerprint enrollment
    
    POST /accounts/api/student/enroll/cancel/
    {
        "student_id": "STU001"
    }
    """
    try:
        data = json.loads(request.body)
        student_id = data.get('student_id')
        
        if not student_id:
            return JsonResponse({
                'status': 'error',
                'message': 'student_id required'
            }, status=400)
        
        try:
            student = CustomUser.objects.get(school_id=student_id, is_student=True)
        except CustomUser.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Student not found'
            }, status=404)
        
        # Find active enrollment
        biometric = BiometricRegistration.objects.filter(
            student=student,
            is_active=True
        ).first()
        
        if not biometric:
            return JsonResponse({
                'status': 'error',
                'message': 'No enrollment in progress'
            }, status=404)
        
        # Release global lock (best-effort)
        try:
            current_lock = cache.get(ENROLLMENT_LOCK_KEY)
            if current_lock and current_lock.get('student_user_id') == student.id:
                cache.delete(ENROLLMENT_LOCK_KEY)
        except Exception:
            pass

        # Cancel via MQTT
        mqtt_client = get_mqtt_client()
        if mqtt_client and mqtt_client.is_connected and biometric.fingerprint_id:
            try:
                cancel_request = {
                    'action': 'cancel_enrollment',
                    'slot': biometric.fingerprint_id
                }
                mqtt_client.publish('biometric/esp32/enroll/request', cancel_request, qos=1)
                logger.info(f"[API] Sent cancel enrollment request for slot {biometric.fingerprint_id}")
            except Exception as e:
                logger.error(f"[API] Failed to send cancel request: {e}")
        
        return JsonResponse({
            'status': 'success',
            'message': 'Enrollment cancelled'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid JSON'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_enrollment_status(request):
    """
    Get current enrollment status for a student
    
    GET /accounts/api/student/enroll/status/?student_id=STU001
    """
    try:
        student_id = request.GET.get('student_id')
        
        if not student_id:
            return JsonResponse({
                'status': 'error',
                'message': 'student_id required'
            }, status=400)
        
        try:
            student = CustomUser.objects.get(school_id=student_id, is_student=True)
        except CustomUser.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Student not found'
            }, status=404)
        
        # Get biometric registrations
        biometrics = BiometricRegistration.objects.filter(
            student=student,
            is_active=True
        )
        
        enrollments = []
        for bio in biometrics:
            enrollments.append({
                'course_code': bio.course.code if bio.course else 'N/A',
                'is_enrolled': bool(bio.fingerprint_id),
                'fingerprint_id': bio.fingerprint_id,
                'enrolled_at': bio.created_at.isoformat() if bio.created_at else None
            })
        
        return JsonResponse({
            'status': 'success',
            'student_id': student_id,
            'enrollments': enrollments,
            'total_enrolled': sum(1 for e in enrollments if e['is_enrolled'])
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def mark_attendance(request):
    """
    Mark student attendance via fingerprint
    
    POST /accounts/api/student/attendance/
    {
        "fingerprint_id": 1,
        "course_id": 1
    }
    """
    try:
        data = json.loads(request.body)
        fingerprint_id = data.get('fingerprint_id')
        course_id = data.get('course_id')
        
        if not fingerprint_id:
            return JsonResponse({
                'status': 'error',
                'message': 'fingerprint_id required'
            }, status=400)
        
        # Find student by fingerprint_id
        biometric = BiometricRegistration.objects.filter(
            fingerprint_id=fingerprint_id,
            is_active=True
        ).first()
        
        if not biometric:
            return JsonResponse({
                'status': 'error',
                'message': 'Fingerprint not registered'
            }, status=404)
        
        return JsonResponse({
            'status': 'success',
            'message': 'Attendance marked',
            'student_name': biometric.student.full_name,
            'course': biometric.course.code if biometric.course else 'Unknown'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid JSON'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_device_status(request):
    """
    Get ESP32 device status
    
    GET /accounts/api/device/status/
    """
    try:
        mqtt_client = get_mqtt_client()
        
        return JsonResponse({
            'status': 'success',
            'device': {
                'name': 'ESP32 R307 Fingerprint System',
                'mqtt_connected': mqtt_client.is_connected if mqtt_client else False,
                'mqtt_broker': 'broker.hivemq.com:1883',
                'available_slots': 127 - BiometricRegistration.objects.filter(is_active=True).count(),
                'total_enrolled': BiometricRegistration.objects.filter(is_active=True, fingerprint_id__isnull=False).count()
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def enrollment_webhook(request):
    """
    Internal webhook called by MQTT bridge when enrollment completes
    
    POST /accounts/api/enrollment/webhook/
    {
        "status": "success",
        "fingerprint_id": 1,
        "session_id": "uuid",
        "slot": 5
    }
    """
    try:
        data = json.loads(request.body)
        status = data.get('status')
        fingerprint_id = data.get('fingerprint_id')
        session_id = data.get('session_id')
        
        if status == 'success' and fingerprint_id:
            # Update biometric record
            biometric = BiometricRegistration.objects.filter(
                fingerprint_id=fingerprint_id
            ).first()
            
            if biometric:
                biometric.is_active = True
                biometric.save()
                
                return JsonResponse({
                    'status': 'success',
                    'message': 'Enrollment completed'
                })
        
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid webhook data'
        }, status=400)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid JSON'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def start_attendance_detection(request):
    """
    Start biometric attendance detection mode on ESP32 via MQTT
    Network-agnostic: works on any network (mobile data, different WiFi, etc.)
    
    POST /accounts/api/instructor/attendance/start/
    {
        "course_id": "CS101",
        "schedule_id": "1",
        "session_id": "uuid"
    }
    
    Returns:
    {
        "status": "success",
        "message": "Attendance detection started",
        "session_id": "uuid"
    }
    """
    try:
        data = json.loads(request.body)
        course_id = data.get('course_id')
        schedule_id = data.get('schedule_id')
        session_id = data.get('session_id') or str(uuid.uuid4())
        
        logger.info(f"[ATTENDANCE API] Received attendance detection request for course {course_id}")
        
        # Get MQTT client to send detection request to ESP32
        mqtt_client = get_mqtt_client()
        if not mqtt_client or not mqtt_client.is_connected:
            logger.error(f"[ATTENDANCE API] MQTT client not connected")
            return JsonResponse({
                'status': 'error',
                'message': 'Biometric service not initialized'
            }, status=503)
        
        logger.info(f"[ATTENDANCE API] MQTT client connected, sending detection request")
        
        # Send detection mode request to ESP32 via MQTT
        # This tells ESP32 to enter attendance detection mode (mode=2)
        detection_request = {
            'action': 'start_detection',
            'mode': 2,  # MODE_ATTENDANCE
            'session_id': session_id,
            'course_id': course_id,
            'schedule_id': schedule_id
        }
        
        topic = 'biometric/esp32/detect/request'
        success = mqtt_client.publish(topic, detection_request, qos=1)
        
        if success:
            logger.info(f"[ATTENDANCE API] Sent detection mode request: {detection_request}")
        else:
            logger.error(f"[ATTENDANCE API] Failed to send detection request to ESP32")
            return JsonResponse({
                'status': 'error',
                'message': 'Failed to start attendance detection'
            }, status=500)
        
        return JsonResponse({
            'status': 'success',
            'message': 'Attendance detection started',
            'session_id': session_id,
            'course_id': course_id,
            'schedule_id': schedule_id
        })
        
    except json.JSONDecodeError:
        logger.error("[ATTENDANCE API] Invalid JSON in request")
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid JSON'
        }, status=400)
    except Exception as e:
        logger.error(f"[ATTENDANCE API] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'status': 'error',
            'message': f'Error: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def start_enrollment_new(request):
    """
    NEW ENDPOINT: Start fingerprint enrollment (from frontend)
    Wrapper that calls start_fingerprint_enrollment with proper parameters
    
    POST /api/start-enrollment/
    {
        "course_id": 1
    }
    """
    try:
        data = json.loads(request.body)
        course_id = data.get('course_id')
        
        if not course_id:
            return JsonResponse({
                'status': 'error',
                'message': 'course_id required'
            }, status=400)
        
        # Generate enrollment and template IDs
        enrollment_id = f"enrollment_{int(time.time() * 1000)}_{''.join([str(uuid.uuid4().hex[i]) for i in range(8)])}"
        template_id = f"template_{int(time.time() * 1000)}_{''.join([str(uuid.uuid4().hex[i]) for i in range(8)])}"
        
        # Get current user
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({
                'status': 'error',
                'message': 'User not authenticated'
            }, status=401)
        
        # Call the existing enrollment function with proper parameters
        request_data = {
            'student_id': user.school_id,
            'enrollment_id': enrollment_id,
            'template_id': template_id,
            'course_id': course_id
        }
        
        logger.info(f"[API] ===== START ENROLLMENT NEW =====")
        logger.info(f"[API] User: {user.school_id}")
        logger.info(f"[API] Request data: {request_data}")
        
        # Create a new request with the properly formatted data
        import copy
        new_request = copy.copy(request)
        new_request.body = json.dumps(request_data).encode('utf-8')
        
        result = start_fingerprint_enrollment(new_request)
        logger.info(f"[API] Result: {result.content}")
        return result
        
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid JSON'
        }, status=400)
    except Exception as e:
        logger.error(f"[API] Error in start_enrollment_new: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'status': 'error',
            'message': f'Error: {str(e)}'
        }, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def debug_enrollment_mappings(request):
    """
    DEBUG ENDPOINT: Check current enrollment ID mappings
    Use this to verify that mappings are being created and maintained
    
    GET /api/student/enroll/debug/
    """
    with enrollment_id_lock:
        mappings = {
            'enrollment_id_map': dict(enrollment_id_map),
            'slot_to_template_map': dict(slot_to_template_map),
            'total_active_enrollments': len(enrollment_id_map),
            'total_occupied_slots': len(slot_to_template_map)
        }
    
    print(f"[DEBUG] Enrollment mappings requested:")
    print(f"[DEBUG] enrollment_id_map: {enrollment_id_map}")
    print(f"[DEBUG] slot_to_template_map: {slot_to_template_map}")
    
    return JsonResponse({
        'status': 'debug',
        'message': 'Current enrollment mappings',
        'data': mappings
    })

@csrf_exempt
@require_http_methods(['POST'])
def stop_attendance_detection(request):
    """
    Stop biometric attendance detection mode on ESP32 via MQTT
    
    POST /accounts/api/instructor/attendance/stop/
    {
        "session_id": "uuid"
    }
    
    Returns:
    {
        "status": "success",
        "message": "Attendance detection stopped"
    }
    """
    try:
        data = json.loads(request.body)
        session_id = data.get('session_id')
        
        logger.info(f"[ATTENDANCE API] Received stop detection request")
        
        # Get MQTT client
        mqtt_client = get_mqtt_client()
        if not mqtt_client or not mqtt_client.is_connected:
            logger.error(f"[ATTENDANCE API] MQTT client not connected")
            return JsonResponse({
                'status': 'error',
                'message': 'Biometric service not initialized'
            }, status=503)
        
        logger.info(f"[ATTENDANCE API] MQTT client connected, sending stop request")
        
        # Send stop detection request to ESP32
        stop_request = {
            'action': 'stop_detection',
            'mode': 0,  # MODE_IDLE
            'session_id': session_id
        }
        
        topic = 'biometric/esp32/detect/request'
        success = mqtt_client.publish(topic, stop_request, qos=1)
        
        if success:
            logger.info(f"[ATTENDANCE API] Sent stop detection request")
        else:
            logger.error(f"[ATTENDANCE API] Failed to send stop request to ESP32")
            return JsonResponse({
                'status': 'error',
                'message': 'Failed to stop attendance detection'
            }, status=500)
        
        return JsonResponse({
            'status': 'success',
            'message': 'Attendance detection stopped',
            'session_id': session_id
        })
        
    except json.JSONDecodeError:
        logger.error("[ATTENDANCE API] Invalid JSON in request")
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid JSON'
        }, status=400)
    except Exception as e:
        logger.error(f"[ATTENDANCE API] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'status': 'error',
            'message': f'Error: {str(e)}'
        }, status=500)
