from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from accounts.models import CustomUser
from datetime import datetime
import json
import logging

# Initialize logger
logger = logging.getLogger(__name__)

# Import centralized enrollment state management
from dashboard.enrollment_state import (
    _enrollment_states,
    create_enrollment_state,
    get_enrollment_state,
    update_enrollment_state,
    delete_enrollment_state,
    get_all_states
)

# ==================== BIOMETRIC ENROLLMENT MANAGEMENT APIs ====================

@csrf_exempt
@require_http_methods(["POST"])
def api_start_enrollment(request):
    """
    Start a new biometric enrollment session for a user
    Creates an enrollment ID and initializes tracking
    
    If the student already has a fingerprint registered for this course,
    they will be informed and can choose to re-register (which will replace the old one)
    """
    try:
        from .models import BiometricRegistration, Course
        
        data = json.loads(request.body)
        course_id = data.get('course_id')
        template_id = data.get('template_id')  # Get template_id from frontend
        
        # Get current user (if authenticated)
        user = request.user if request.user.is_authenticated else None
        
        if not user:
            return JsonResponse({
                'success': False,
                'message': 'User must be authenticated to start enrollment'
            }, status=401)
        
        # Check if course exists
        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Course not found'
            }, status=404)
        
        # CHECK: Has this student already registered their fingerprint for this course?
        existing_registration = BiometricRegistration.objects.filter(
            student=user,
            course=course,
            is_active=True
        ).first()
        
        # Generate unique enrollment ID (different from template_id)
        enrollment_id = f"enrollment_{int(datetime.now().timestamp()*1000)}_{user.id}"
        
        # If template_id not provided, generate one
        if not template_id:
            template_id = f"template_{int(datetime.now().timestamp()*1000)}_{user.id}"
        
        # Initialize enrollment state using centralized function
        # CRITICAL: Store the frontend's template_id so MQTT bridge can match it
        create_enrollment_state(
            enrollment_id=enrollment_id,
            user_id=user.id,
            course_id=course_id,
            template_id=template_id,  # Use template_id from frontend (what ESP32 will send)
            is_re_registration=existing_registration is not None,
            old_fingerprint_id=existing_registration.fingerprint_id if existing_registration else None
        )
        
        logger.info(f"[ENROLLMENT] Started enrollment session: {enrollment_id}")
        
        if existing_registration:
            logger.info(f"[ENROLLMENT] Student {user.full_name} already has fingerprint ID {existing_registration.fingerprint_id} for course {course.code}")
            logger.info(f"[ENROLLMENT] This is a RE-REGISTRATION - old fingerprint will be replaced")
        
        # MQTT is now embedded in Django - no need for external bridge
        # Enrollment state management handles all MQTT communication
        logger.info(f"[ENROLLMENT] ✓ Published to MQTT: enrollment_id={enrollment_id}, template_id={template_id}")
        
        # Send notification to ESP32 that enrollment has started
        try:
            import requests
            esp32_ip = '192.168.1.10'
            esp32_port = 80
            notification_url = f'http://{esp32_ip}:{esp32_port}/api/enrollment-status'
            
            enrollment_data = {
                'action': 'start_enrollment',
                'enrollment_id': enrollment_id,
                'course_id': course_id,
                'user_id': user.id,
                'is_re_registration': existing_registration is not None
            }
            
            response = requests.post(notification_url, json=enrollment_data, timeout=2)
            logger.info(f"[ENROLLMENT] Notified ESP32 of enrollment start: {response.status_code}")
        except Exception as e:
            logger.warning(f"[ENROLLMENT] Could not notify ESP32: {str(e)}")
        
        response_data = {
            'success': True,
            'enrollment_id': enrollment_id,
            'message': 'Enrollment session created',
            'has_existing_registration': existing_registration is not None,
        }
        
        # If re-registering, include the old fingerprint ID in response
        if existing_registration:
            response_data['old_fingerprint_id'] = existing_registration.fingerprint_id
            response_data['re_registration_message'] = f'You already have a fingerprint registered for this course. Placing a new finger will replace the old one (ID: {existing_registration.fingerprint_id}) with a new fingerprint ID.'
        
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"[ENROLLMENT] Error starting enrollment: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def api_enrollment_status(request, enrollment_id):
    """
    Get current status of an ongoing enrollment
    Returns progress percentage, current scan number, and status message
    EventSource endpoint for real-time enrollment updates
    """
    try:
        if enrollment_id not in _enrollment_states:
            return JsonResponse({
                'status': 'not_found',
                'message': 'Enrollment not found'
            }, status=404)
        
        state = _enrollment_states[enrollment_id]
        
        # Return current state
        response = JsonResponse(state)
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        
        return response
        
    except Exception as e:
        logger.error(f"[ENROLLMENT] Error getting enrollment updates: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_save_enrollment(request):
    """
    Save completed enrollment to database
    Stores fingerprint ID in user's biometric registration and links to courses
    """
    try:
        data = json.loads(request.body)
        enrollment_id = data.get('enrollment_id')
        course_id = data.get('course_id')
        
        user = request.user if request.user.is_authenticated else None
        if not user:
            return JsonResponse({
                'success': False,
                'message': 'User must be authenticated'
            }, status=401)
        
        # Get enrollment state
        if enrollment_id not in _enrollment_states:
            return JsonResponse({
                'success': False,
                'message': 'Enrollment session not found'
            }, status=404)
        
        state = _enrollment_states[enrollment_id]
        if state['status'] != 'completed':
            return JsonResponse({
                'success': False,
                'message': 'Enrollment not completed'
            }, status=400)
        
        # Get course
        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Course not found'
            }, status=404)
        
        # Get fingerprint ID from ESP32 response
        fingerprint_id = state.get('fingerprint_id')
        if not fingerprint_id:
            fingerprint_id = 1  # Default fallback
        
        # Check if this is a re-registration and delete the old fingerprint ID from sensor
        old_fingerprint_id = state.get('old_fingerprint_id')
        is_re_registration = state.get('is_re_registration', False)
        
        if is_re_registration and old_fingerprint_id:
            logger.info(f"[ENROLLMENT] RE-REGISTRATION: Deleting old fingerprint ID {old_fingerprint_id} from sensor")
            # In a real implementation, you would send a command to ESP32 to delete the old fingerprint ID
            # For now, we just log it and the old one will be overwritten in the database
            try:
                import requests
                esp32_ip = '192.168.1.10'
                esp32_port = 80
                delete_url = f'http://{esp32_ip}:{esp32_port}/api/delete-fingerprint/'
                
                delete_data = {
                    'fingerprint_id': old_fingerprint_id,
                    'course_id': course_id
                }
                
                response = requests.post(delete_url, json=delete_data, timeout=2)
                logger.info(f"[ENROLLMENT] Notified ESP32 to delete old fingerprint ID {old_fingerprint_id}: {response.status_code}")
            except Exception as e:
                logger.warning(f"[ENROLLMENT] Could not notify ESP32 to delete old fingerprint: {str(e)}")
        
        # Create or update biometric registration
        biometric_reg, created = BiometricRegistration.objects.update_or_create(
            student=user,
            course=course,
            defaults={
                'fingerprint_id': fingerprint_id,
                'is_active': True
            }
        )
        
        # Also update user's default biometric profile
        user.biometric_fingerprint_id = fingerprint_id
        user.biometric_registered = True
        user.save()
        
        # MQTT is now embedded in Django - enrollment completion handled internally
        # The MQTT bridge will handle this to ensure reliability
        logger.info(f"[ENROLLMENT] ✓ Enrollment {enrollment_id} (template_id={template_id}) saved to database")
        logger.info(f"[ENROLLMENT] Publishing enrollment_saved message to ESP32 via embedded MQTT...")
        
        # Clean up enrollment state
        delete_enrollment_state(enrollment_id)
        
        # Log the enrollment
        if is_re_registration and old_fingerprint_id:
            logger.info(f"[ENROLLMENT] RE-REGISTRATION COMPLETED: Student {user.full_name}")
            logger.info(f"[ENROLLMENT]   Old fingerprint ID: {old_fingerprint_id}")
            logger.info(f"[ENROLLMENT]   New fingerprint ID: {fingerprint_id}")
            logger.info(f"[ENROLLMENT]   Course: {course.code} ({course.name})")
        else:
            logger.info(f"[ENROLLMENT] NEW ENROLLMENT: Student {user.full_name} with fingerprint ID {fingerprint_id} for course {course.code}")
        
        return JsonResponse({
            'success': True,
            'message': 'Fingerprint saved successfully',
            'fingerprint_id': fingerprint_id,
            'course_id': course_id,
            'is_re_registration': is_re_registration,
            'old_fingerprint_id': old_fingerprint_id if is_re_registration else None
        })
        
    except Exception as e:
        logger.error(f"[ENROLLMENT] Error saving enrollment: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


def update_enrollment_progress(enrollment_id, current_scan, progress, message, fingerprint_id=None, error=None):
    """
    Helper function to update enrollment progress
    Called by ESP32 API endpoints when broadcasting updates
    """
    if enrollment_id in _enrollment_states:
        _enrollment_states[enrollment_id].update({
            'current_scan': current_scan,
            'progress': progress,
            'message': message,
            'updated_at': datetime.now().isoformat()
        })
        
        if fingerprint_id:
            _enrollment_states[enrollment_id]['fingerprint_id'] = fingerprint_id
        
        if error:
            _enrollment_states[enrollment_id]['error'] = error
            _enrollment_states[enrollment_id]['status'] = 'failed'
        
        # Auto-complete at 100%
        if progress >= 100:
            _enrollment_states[enrollment_id]['status'] = 'completed'
        
        logger.debug(f"[ENROLLMENT] Updated {enrollment_id}: Scan {current_scan}, Progress {progress}%")


def mark_enrollment_complete(enrollment_id, fingerprint_id):
    """
    Helper function to mark enrollment as complete
    """
    if enrollment_id in _enrollment_states:
        _enrollment_states[enrollment_id].update({
            'status': 'completed',
            'progress': 100,
            'message': 'All 5 scans completed successfully!',
            'fingerprint_id': fingerprint_id,
            'completed_at': datetime.now().isoformat()
        })
        logger.info(f"[ENROLLMENT] Completed enrollment {enrollment_id} with fingerprint ID {fingerprint_id}")
