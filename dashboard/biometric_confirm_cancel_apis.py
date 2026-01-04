# Biometric Confirmation and Cancellation APIs
# These APIs handle the confirmation and cancellation of biometric enrollments
# They proxy requests to the ESP32 device to avoid CORS issues

import json
import logging
import requests
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from .models import BiometricRegistration, CourseEnrollment, Course

logger = logging.getLogger(__name__)

# ESP32 Configuration - use environment variable or fallback
ESP32_IP = settings.ESP32_IP
ESP32_PORT = 80
ESP32_TIMEOUT = 10  # seconds


@csrf_exempt
@require_http_methods(["POST"])
def api_biometric_confirm_enrollment(request):
    """
    Confirm a biometric enrollment and save to database
    This endpoint:
    1. Sends confirmation to ESP32 (via HTTP proxy to avoid CORS)
    2. Saves the biometric registration in Django database
    3. Associates the fingerprint with all enrolled courses
    """
    try:
        data = json.loads(request.body)
        
        fingerprint_id = data.get('fingerprint_id', 1)
        template_id = data.get('template_id', '')
        is_replacement = data.get('is_replacement', False)
        course_ids = data.get('course_ids', [])
        
        # Get authenticated user
        user = request.user
        if not user or not user.is_authenticated:
            return JsonResponse({
                'success': False,
                'message': 'User must be authenticated'
            }, status=401)
        
        logger.info(f"[CONFIRM] Confirming enrollment for user {user.full_name}")
        logger.info(f"[CONFIRM] Fingerprint ID: {fingerprint_id}, Template: {template_id}")
        logger.info(f"[CONFIRM] Is Replacement: {is_replacement}, Courses: {course_ids}")
        
        # Step 1: Send confirmation to ESP32
        esp32_url = f'http://{ESP32_IP}:{ESP32_PORT}/enroll/confirm'
        esp32_payload = {
            'fingerprint_id': fingerprint_id,
            'template_id': template_id
        }
        
        logger.info(f"[CONFIRM] Sending confirmation to ESP32 at {esp32_url}")
        
        try:
            esp32_response = requests.post(
                esp32_url,
                json=esp32_payload,
                timeout=ESP32_TIMEOUT
            )
            
            if esp32_response.status_code != 200:
                logger.warning(f"[CONFIRM] ESP32 returned status {esp32_response.status_code}")
                logger.warning(f"[CONFIRM] Response: {esp32_response.text}")
            else:
                logger.info(f"[CONFIRM] ✓ ESP32 confirmation successful")
                
        except requests.exceptions.RequestException as e:
            logger.warning(f"[CONFIRM] Could not reach ESP32: {str(e)}")
            logger.warning(f"[CONFIRM] Continuing with database save anyway")
        
        # Step 2: Save biometric registration in database for each course
        saved_count = 0
        
        if course_ids:
            for course_id in course_ids:
                try:
                    course = Course.objects.get(id=course_id)
                    
                    # Check if registration already exists (replacement case)
                    existing_reg = BiometricRegistration.objects.filter(
                        student=user,
                        course=course,
                        is_active=True
                    ).first()
                    
                    if existing_reg:
                        # Update existing registration
                        existing_reg.fingerprint_id = fingerprint_id
                        existing_reg.template_id = template_id
                        existing_reg.save()
                        logger.info(f"[CONFIRM] ✓ Updated existing registration for course {course.code}")
                    else:
                        # Create new registration
                        bio_reg = BiometricRegistration(
                            student=user,
                            course=course,
                            fingerprint_id=fingerprint_id,
                            template_id=template_id,
                            is_active=True
                        )
                        bio_reg.save()
                        logger.info(f"[CONFIRM] ✓ Created new registration for course {course.code}")
                    
                    saved_count += 1
                    
                except Course.DoesNotExist:
                    logger.warning(f"[CONFIRM] Course {course_id} not found")
                except Exception as e:
                    logger.error(f"[CONFIRM] Error saving registration for course {course_id}: {str(e)}")
        
        logger.info(f"[CONFIRM] ✓✓✓ Confirmation complete - {saved_count} courses registered")
        
        return JsonResponse({
            'success': True,
            'message': f'Fingerprint confirmed successfully for {saved_count} course(s)',
            'fingerprint_id': fingerprint_id,
            'is_replacement': is_replacement,
            'confirmed_courses': saved_count
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f"[CONFIRM] Error confirming enrollment: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_biometric_cancel_enrollment(request):
    """
    Cancel an ongoing biometric enrollment
    This endpoint:
    1. Sends cancellation request to ESP32
    2. Cleans up enrollment session
    """
    try:
        # Get authenticated user
        user = request.user
        if not user or not user.is_authenticated:
            return JsonResponse({
                'success': False,
                'message': 'User must be authenticated'
            }, status=401)
        
        logger.info(f"[CANCEL] Cancelling enrollment for user {user.full_name}")
        
        # Send cancellation to ESP32
        esp32_url = f'http://{ESP32_IP}:{ESP32_PORT}/enroll/cancel'
        
        logger.info(f"[CANCEL] Sending cancellation to ESP32 at {esp32_url}")
        
        try:
            esp32_response = requests.post(
                esp32_url,
                json={},
                timeout=ESP32_TIMEOUT
            )
            
            if esp32_response.status_code == 200:
                logger.info(f"[CANCEL] ✓ ESP32 cancellation successful")
            else:
                logger.warning(f"[CANCEL] ESP32 returned status {esp32_response.status_code}")
                
        except requests.exceptions.RequestException as e:
            logger.warning(f"[CANCEL] Could not reach ESP32: {str(e)}")
            logger.warning(f"[CANCEL] User-side cancellation will still work")
        
        logger.info(f"[CANCEL] ✓ Enrollment cancelled")
        
        return JsonResponse({
            'success': True,
            'message': 'Enrollment cancelled'
        })
        
    except Exception as e:
        logger.error(f"[CANCEL] Error cancelling enrollment: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'message': str(e)}, status=500)
