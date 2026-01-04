# API endpoints for biometric enrollment management
# This file contains the new APIs for frontend enrollment handling

import json
import logging
import requests
from datetime import datetime
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.conf import settings
from .models import BiometricRegistration, CourseEnrollment, Course
from accounts.models import CustomUser

logger = logging.getLogger(__name__)

# ESP32 Server Address
ESP32_SERVER = getattr(settings, 'ESP32_SERVER', 'http://192.168.1.8')  # Default to 192.168.1.8

# In-memory store for current enrollment states (in production, use Redis or database)
enrollment_states = {}

@csrf_exempt
@require_http_methods(["POST"])
def api_start_enrollment(request):
    """
    Start a new biometric enrollment session for a user
    Creates an enrollment ID and initializes tracking
    Also forwards the request to ESP32 to start enrollment
    """
    try:
        data = json.loads(request.body)
        course_id = data.get('course_id')
        
        # Get current user (if authenticated)
        user = request.user if request.user.is_authenticated else None
        
        # Generate unique enrollment ID
        enrollment_id = f"enrollment_{int(datetime.now().timestamp()*1000)}_{user.id if user else 'anonymous'}"
        
        # Initialize enrollment state
        enrollment_states[enrollment_id] = {
            'status': 'processing',
            'current_scan': 0,
            'progress': 0,
            'message': 'Initializing enrollment...',
            'course_id': course_id,
            'user_id': user.id if user else None,
            'created_at': datetime.now().isoformat(),
            'scans': []
        }
        
        logger.info(f"[ENROLLMENT] Started enrollment session: {enrollment_id}")
        
        # Forward enrollment request to ESP32
        try:
            esp32_url = f"{ESP32_SERVER}/enroll"
            payload = {
                'slot': course_id,  # Use course_id as slot number
                'template_id': enrollment_id
            }
            
            logger.info(f"[ENROLLMENT] Forwarding to ESP32 at {esp32_url} with payload: {payload}")
            
            # Send request to ESP32 with timeout
            response = requests.post(
                esp32_url,
                json=payload,
                timeout=5
            )
            
            if response.status_code == 200:
                logger.info(f"[ENROLLMENT] ESP32 acknowledged enrollment request")
                enrollment_states[enrollment_id]['message'] = 'ESP32 sensor ready - place your finger'
            else:
                logger.warning(f"[ENROLLMENT] ESP32 returned status {response.status_code}")
                enrollment_states[enrollment_id]['message'] = 'ESP32 acknowledged request'
                
        except requests.exceptions.ConnectionError:
            logger.error(f"[ENROLLMENT] Cannot connect to ESP32 at {ESP32_SERVER}")
            enrollment_states[enrollment_id]['message'] = 'Waiting for sensor... (ESP32 may be offline)'
        except requests.exceptions.Timeout:
            logger.error(f"[ENROLLMENT] Timeout connecting to ESP32")
            enrollment_states[enrollment_id]['message'] = 'Sensor connection timeout'
        except Exception as e:
            logger.error(f"[ENROLLMENT] Error forwarding to ESP32: {str(e)}")
            enrollment_states[enrollment_id]['message'] = f'Error: {str(e)}'
        
        return JsonResponse({
            'success': True,
            'enrollment_id': enrollment_id,
            'message': 'Enrollment session created and forwarded to ESP32'
        })
        
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
    """
    try:
        # Check if enrollment exists in memory
        if enrollment_id in enrollment_states:
            state = enrollment_states[enrollment_id]
            return JsonResponse({
                'status': state['status'],
                'current_scan': state.get('current_scan', 0),
                'progress': state.get('progress', 0),
                'message': state.get('message', ''),
                'error': state.get('error', None)
            })
        else:
            return JsonResponse({
                'status': 'not_found',
                'message': 'Enrollment session not found'
            }, status=404)
            
    except Exception as e:
        logger.error(f"[ENROLLMENT] Error getting enrollment status: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def api_enrollment_updates(request, enrollment_id):
    """
    EventSource endpoint for real-time enrollment updates
    (Can be converted to WebSocket in future)
    """
    try:
        if enrollment_id not in enrollment_states:
            return JsonResponse({
                'status': 'not_found',
                'message': 'Enrollment not found'
            }, status=404)
        
        state = enrollment_states[enrollment_id]
        
        # Return current state as SSE event
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
        if enrollment_id not in enrollment_states:
            return JsonResponse({
                'success': False,
                'message': 'Enrollment session not found'
            }, status=404)
        
        state = enrollment_states[enrollment_id]
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
        
        # Create or update biometric registration
        biometric_reg, created = BiometricRegistration.objects.update_or_create(
            user=user,
            course=course,
            defaults={
                'fingerprint_id': fingerprint_id,
                'status': 'active',
                'registered_at': datetime.now(),
                'enrollment_session_id': enrollment_id
            }
        )
        
        # Also update user's default biometric profile (for future attendance)
        if user.is_instructor or user.is_staff:
            # Store fingerprint ID at user level too
            user.biometric_fingerprint_id = fingerprint_id
            user.biometric_registered = True
            user.save()
        
        # Clean up enrollment state
        del enrollment_states[enrollment_id]
        
        logger.info(f"[ENROLLMENT] Saved enrollment {enrollment_id} with fingerprint ID {fingerprint_id} for course {course_id}")
        
        return JsonResponse({
            'success': True,
            'message': 'Fingerprint saved successfully',
            'fingerprint_id': fingerprint_id,
            'course_id': course_id
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
    if enrollment_id in enrollment_states:
        enrollment_states[enrollment_id].update({
            'current_scan': current_scan,
            'progress': progress,
            'message': message,
            'updated_at': datetime.now().isoformat()
        })
        
        if fingerprint_id:
            enrollment_states[enrollment_id]['fingerprint_id'] = fingerprint_id
        
        if error:
            enrollment_states[enrollment_id]['error'] = error
            enrollment_states[enrollment_id]['status'] = 'failed'
        
        # Auto-complete at 100%
        if progress >= 100:
            enrollment_states[enrollment_id]['status'] = 'completed'
        
        logger.debug(f"[ENROLLMENT] Updated {enrollment_id}: Scan {current_scan}, Progress {progress}%")


def mark_enrollment_complete(enrollment_id, fingerprint_id):
    """
    Helper function to mark enrollment as complete
    Called when all 5 scans are successfully completed
    """
    if enrollment_id in enrollment_states:
        enrollment_states[enrollment_id].update({
            'status': 'completed',
            'progress': 100,
            'message': 'All 5 scans completed successfully!',
            'fingerprint_id': fingerprint_id,
            'completed_at': datetime.now().isoformat()
        })
        logger.info(f"[ENROLLMENT] Completed enrollment {enrollment_id} with fingerprint ID {fingerprint_id}")
