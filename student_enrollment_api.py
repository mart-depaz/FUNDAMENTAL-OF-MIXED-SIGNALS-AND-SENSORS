"""
API views for student fingerprint enrollment and attendance
Works with MQTT bridge - students can use any network
"""

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
import json
import uuid
from mqtt_bridge import get_mqtt_bridge
from accounts.models import BiometricData, Student
from django.utils import timezone

@csrf_exempt
@require_http_methods(["POST"])
@login_required
def start_fingerprint_enrollment(request):
    """
    Student starts fingerprint enrollment
    Works from any network (mobile, different WiFi, etc.)
    
    POST /api/student/enroll/start/
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
        
        # Get or create biometric record
        try:
            student = Student.objects.get(student_id=student_id)
            biometric, created = BiometricData.objects.get_or_create(
                student=student,
                defaults={'fingerprint_template_id': str(uuid.uuid4())}
            )
        except Student.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Student not found'
            }, status=404)
        
        # Check if already enrolled
        if biometric.is_enrolled and biometric.slot_number:
            return JsonResponse({
                'status': 'error',
                'message': 'Fingerprint already enrolled'
            }, status=400)
        
        # Find available slot (1-127)
        occupied_slots = BiometricData.objects.filter(
            is_enrolled=True
        ).values_list('slot_number', flat=True)
        
        available_slot = None
        for slot in range(1, 128):
            if slot not in occupied_slots:
                available_slot = slot
                break
        
        if not available_slot:
            return JsonResponse({
                'status': 'error',
                'message': 'No available fingerprint slots'
            }, status=400)
        
        # Request enrollment via MQTT
        mqtt_bridge = get_mqtt_bridge()
        mqtt_bridge.request_enrollment(
            slot=available_slot,
            student_id=student_id,
            template_id=biometric.fingerprint_template_id
        )
        
        # Update biometric record
        biometric.enrollment_started_at = timezone.now()
        biometric.enrollment_session_id = str(uuid.uuid4())
        biometric.save()
        
        return JsonResponse({
            'status': 'success',
            'message': 'Enrollment started',
            'session_id': biometric.enrollment_session_id,
            'slot': available_slot,
            'next_step': 'Place your finger on the sensor'
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def cancel_fingerprint_enrollment(request):
    """
    Cancel ongoing fingerprint enrollment
    
    POST /api/student/enroll/cancel/
    {
        "student_id": "STU001"
    }
    """
    try:
        data = json.loads(request.body)
        student_id = data.get('student_id')
        
        try:
            student = Student.objects.get(student_id=student_id)
            biometric = BiometricData.objects.get(student=student)
        except BiometricData.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'No enrollment in progress'
            }, status=404)
        
        # Cancel via MQTT
        mqtt_bridge = get_mqtt_bridge()
        mqtt_bridge.cancel_enrollment(biometric.slot_number or 0)
        
        # Reset enrollment fields
        biometric.enrollment_started_at = None
        biometric.enrollment_session_id = None
        biometric.save()
        
        return JsonResponse({
            'status': 'success',
            'message': 'Enrollment cancelled'
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
@login_required
def get_enrollment_status(request):
    """
    Check enrollment status
    
    GET /api/student/enroll/status/?student_id=STU001
    """
    try:
        student_id = request.GET.get('student_id')
        
        try:
            student = Student.objects.get(student_id=student_id)
            biometric = BiometricData.objects.get(student=student)
        except BiometricData.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'No biometric record found'
            }, status=404)
        
        return JsonResponse({
            'status': 'success',
            'is_enrolled': biometric.is_enrolled,
            'enrollment_in_progress': biometric.enrollment_session_id is not None,
            'last_enrollment_at': biometric.enrolled_at.isoformat() if biometric.enrolled_at else None,
            'last_enrollment_attempt': biometric.enrollment_started_at.isoformat() if biometric.enrollment_started_at else None
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def mark_attendance(request):
    """
    Submit fingerprint for attendance marking
    Can be called from any network
    
    POST /api/student/attendance/
    {
        "student_id": "STU001",
        "course_id": "CS101"
    }
    """
    try:
        data = json.loads(request.body)
        student_id = data.get('student_id')
        course_id = data.get('course_id')
        
        if not student_id or not course_id:
            return JsonResponse({
                'status': 'error',
                'message': 'student_id and course_id required'
            }, status=400)
        
        try:
            student = Student.objects.get(student_id=student_id)
            biometric = BiometricData.objects.get(student=student)
        except BiometricData.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Fingerprint not enrolled'
            }, status=404)
        
        if not biometric.is_enrolled:
            return JsonResponse({
                'status': 'error',
                'message': 'Fingerprint not enrolled'
            }, status=400)
        
        # Enable detection mode on ESP32
        mqtt_bridge = get_mqtt_bridge()
        mqtt_bridge.enable_detection(mode="attendance")
        
        return JsonResponse({
            'status': 'success',
            'message': 'Waiting for fingerprint...',
            'timeout_seconds': 30
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
    Webhook called by ESP32 (via MQTT) when enrollment completes
    This is called from MQTT bridge, not directly by students
    
    Internal endpoint
    """
    try:
        data = json.loads(request.body)
        status = data.get('status')
        template_id = data.get('template_id')
        slot = data.get('slot')
        
        if status == 'success':
            try:
                biometric = BiometricData.objects.get(
                    fingerprint_template_id=template_id
                )
                biometric.is_enrolled = True
                biometric.slot_number = slot
                biometric.enrolled_at = timezone.now()
                biometric.enrollment_session_id = None
                biometric.enrollment_started_at = None
                biometric.save()
                
                return JsonResponse({
                    'status': 'success',
                    'message': 'Enrollment recorded'
                })
            except BiometricData.DoesNotExist:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Biometric record not found'
                }, status=404)
        
        return JsonResponse({
            'status': 'error',
            'message': 'Unknown status'
        }, status=400)
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
@login_required
def get_device_status(request):
    """
    Get current ESP32 device status
    
    GET /api/device/status/
    """
    try:
        mqtt_bridge = get_mqtt_bridge()
        
        # Request device info
        mqtt_bridge.send_command("sensor_info")
        
        return JsonResponse({
            'status': 'success',
            'message': 'Device status request sent',
            'device_connected': mqtt_bridge.is_connected
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)
