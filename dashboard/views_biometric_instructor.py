# This file contains the biometric instructor scanning views
# These will be added to the main views.py file

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import datetime, date
import json
import logging

# Configure logger
logger = logging.getLogger('biometric_attendance')


@login_required
@require_http_methods(["GET"])
def instructor_get_biometric_pending_view(request):
    """
    Get pending biometric scans for a course (from ESP32 sensor).
    Called by JavaScript polling to check for new fingerprint detections.
    
    Query parameters:
    - course_id: int (required)
    - schedule_id: str (optional)
    
    Returns:
    {
        'pending': [
            {
                'fingerprint_id': int,
                'student_id': int,
                'student_name': str,
                'confidence': int,
                'timestamp': str
            }
        ]
    }
    """
    try:
        if not request.user.is_teacher:
            return JsonResponse({'pending': []})
        
        course_id = request.GET.get('course_id')
        schedule_id = request.GET.get('schedule_id')
        
        if not course_id:
            return JsonResponse({'pending': []})
        
        from dashboard.models import Course, BiometricRegistration
        from django.core.cache import cache
        
        try:
            course = Course.objects.get(id=int(course_id))
        except (Course.DoesNotExist, ValueError):
            return JsonResponse({'pending': []})
        
        # Get all biometric registrations for this course that are active
        registrations = BiometricRegistration.objects.filter(
            course=course,
            is_active=True
        ).select_related('student')
        
        # Create a mapping of fingerprint_id -> (student, registration)
        # fingerprint_id is the ESP32 slot number where the fingerprint is stored
        fingerprint_map = {}
        for reg in registrations:
            if reg.fingerprint_id:
                fingerprint_map[reg.fingerprint_id] = {
                    'student': reg.student,
                    'registration': reg,
                    'fingerprint_id': reg.fingerprint_id
                }
        
        logger.info(f"[POLLING] Course {course.code}: Found {len(fingerprint_map)} registered fingerprints - {list(fingerprint_map.keys())}")
        
        # Get pending detections from cache
        detections_queue_key = "fingerprint_detections_queue"
        queue = cache.get(detections_queue_key, [])
        
        pending_list = []
        processed_keys = []
        
        # Process each detection
        for detection in queue:
            fingerprint_slot = detection.get('fingerprint_id')
            confidence = detection.get('confidence', 0)
            timestamp = detection.get('timestamp')
            detection_key = detection.get('key')
            
            logger.info(f"[PENDING] Checking detection - Slot: {fingerprint_slot}, Confidence: {confidence}")
            
            # Check if this fingerprint is registered for this course
            if fingerprint_slot in fingerprint_map:
                student_info = fingerprint_map[fingerprint_slot]
                student = student_info['student']
                
                pending_list.append({
                    'fingerprint_id': fingerprint_slot,
                    'fingerprint_template_id': student_info.get('fingerprint_id', ''),
                    'student_id': student.id,
                    'student_name': student.full_name or student.username,
                    'student_email': student.email,
                    'confidence': confidence,
                    'timestamp': timestamp
                })
                
                logger.info(f"[PENDING] Match found - Student: {student.full_name}")
                processed_keys.append(detection_key)
                
            elif fingerprint_slot == -1:
                # Unregistered fingerprint
                pending_list.append({
                    'fingerprint_id': -1,
                    'student_id': None,
                    'student_name': 'Unregistered',
                    'error': 'unregistered_fingerprint',
                    'confidence': confidence,
                    'timestamp': timestamp
                })
                logger.warning(f"[PENDING] Unregistered fingerprint detected")
                processed_keys.append(detection_key)
        
        # Remove processed detections from queue (clean up)
        if processed_keys:
            queue = [d for d in queue if d.get('key') not in processed_keys]
            cache.set(detections_queue_key, queue, 60)
            logger.info(f"[PENDING] Removed {len(processed_keys)} processed detections, {len(queue)} remaining in queue")
        
        logger.info(f"[PENDING] Returning {len(pending_list)} pending detections for course {course_id}")
        return JsonResponse({'pending': pending_list})
        
    except Exception as e:
        logger.error(f"Error getting pending biometric scans: {str(e)}", exc_info=True)
        return JsonResponse({'pending': []})


@login_required
@require_http_methods(["POST"])
def instructor_biometric_scan_attendance_view(request):
    """
    Record attendance via biometric scan (instructor context).
    Called when a student's fingerprint is verified through the instructor interface.
    
    Expected POST data:
    {
        'course_id': <int>,
        'fingerprint_id': '<str>', # fingerprint template ID from ESP32
        'schedule_id': '<str>' (optional)
    }
    """
    try:
        if not request.user.is_teacher:
            return JsonResponse({
                'success': False,
                'message': 'Only instructors can process biometric scans.'
            }, status=403)
        
        from django.db import transaction
        from accounts.models import CustomUser
        from dashboard.models import (
            Course, BiometricRegistration, AttendanceRecord, 
            CourseEnrollment, CourseSchedule
        )
        
        data = json.loads(request.body)
        course_id = data.get('course_id')
        fingerprint_id = data.get('fingerprint_id', '').strip()
        schedule_id = data.get('schedule_id', '')
        
        if not course_id or not fingerprint_id:
            return JsonResponse({
                'success': False,
                'message': 'Missing course_id or fingerprint_id'
            }, status=400)
        
        # Get course
        try:
            course = Course.objects.get(id=int(course_id))
        except (Course.DoesNotExist, ValueError):
            return JsonResponse({
                'success': False,
                'message': 'Course not found'
            }, status=404)
        
        # Find student with matching fingerprint registration for this course
        biometric_reg = BiometricRegistration.objects.filter(
            course=course,
            fingerprint_id=fingerprint_id,
            is_active=True
        ).select_related('student').first()
        
        if not biometric_reg:
            return JsonResponse({
                'success': False,
                'message': 'Fingerprint not registered for this course'
            }, status=403)
        
        student = biometric_reg.student
        
        # Get student's enrollment
        try:
            enrollment = CourseEnrollment.objects.get(
                student=student,
                course=course,
                is_active=True
            )
        except CourseEnrollment.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Student is not enrolled in this course'
            }, status=403)
        
        # Check if attendance is open (prefer schedule-level when schedule_id provided)
        attendance_status = getattr(course, 'attendance_status', None)

        active_schedule = None
        if schedule_id:
            try:
                parts = str(schedule_id).split('_')
                if len(parts) >= 2:
                    day_token = parts[1]
                    day_map_reverse = {
                        'M': 'Mon', 'T': 'Tue', 'W': 'Wed', 'Th': 'Thu', 'F': 'Fri',
                        'S': 'Sat', 'Su': 'Sun',
                        'Mon': 'Mon', 'Tue': 'Tue', 'Wed': 'Wed', 'Thu': 'Thu', 'Fri': 'Fri', 'Sat': 'Sat', 'Sun': 'Sun'
                    }
                    mapped_day = day_map_reverse.get(day_token)
                    if mapped_day:
                        active_schedule = CourseSchedule.objects.filter(course=course, day=mapped_day).first()
            except Exception:
                active_schedule = None

        try:
            if active_schedule and getattr(active_schedule, 'attendance_status', None):
                attendance_status = active_schedule.attendance_status
        except Exception:
            pass

        if attendance_status not in ['open', 'automatic']:
            return JsonResponse({
                'success': False,
                'message': f'Attendance is currently {attendance_status}. Cannot record attendance.'
            }, status=403)
        
        # Record attendance
        try:
            ph_tz = timezone.get_fixed_timezone(timezone.timedelta(hours=8))
        except:
            from zoneinfo import ZoneInfo
            try:
                ph_tz = ZoneInfo('Asia/Manila')
            except:
                import pytz
                ph_tz = pytz.timezone('Asia/Manila')
        
        now_ph = timezone.now().astimezone(ph_tz)
        today = now_ph.date()
        
        # Determine schedule day
        schedule_day = None
        if active_schedule:
            schedule_day = active_schedule.day
        
        # Check for existing attendance record
        existing_record = AttendanceRecord.objects.filter(
            student=student,
            course=course,
            attendance_date=today,
            schedule_day=schedule_day or ''
        ).first()
        
        if existing_record and existing_record.status in ['present', 'late']:
            return JsonResponse({
                'success': False,
                'message': f'Student already marked as {existing_record.status} today'
            }, status=409)
        
        # Determine attendance status (present/late)
        attendance_record_status = 'present'

        present_duration_minutes = None
        qr_opened_at = None
        try:
            if active_schedule and getattr(active_schedule, 'attendance_present_duration', None) is not None:
                present_duration_minutes = int(active_schedule.attendance_present_duration or 0)
            else:
                present_duration_minutes = int(getattr(course, 'attendance_present_duration', 0) or 0)
        except Exception:
            present_duration_minutes = 0

        try:
            if active_schedule and getattr(active_schedule, 'qr_code_opened_at', None):
                qr_opened_at = active_schedule.qr_code_opened_at
            else:
                qr_opened_at = getattr(course, 'qr_code_opened_at', None)
        except Exception:
            qr_opened_at = None

        # Prefer using qr_opened_at baseline when available
        cutoff_dt = None
        if present_duration_minutes and present_duration_minutes > 0:
            try:
                if qr_opened_at:
                    cutoff_dt = qr_opened_at + timezone.timedelta(minutes=int(present_duration_minutes))
                elif active_schedule and getattr(active_schedule, 'start_time', None):
                    from datetime import datetime as dt
                    cutoff_dt = dt.combine(today, active_schedule.start_time) + timezone.timedelta(minutes=int(present_duration_minutes))
                    try:
                        cutoff_dt = cutoff_dt.replace(tzinfo=now_ph.tzinfo)
                    except Exception:
                        pass
            except Exception:
                cutoff_dt = None

        if cutoff_dt and now_ph > cutoff_dt:
            attendance_record_status = 'late'
        elif not cutoff_dt:
            # Fallback: use attendance_end window if configured
            try:
                end_time = None
                if active_schedule and getattr(active_schedule, 'attendance_end', None):
                    end_time = active_schedule.attendance_end
                elif getattr(course, 'attendance_end', None):
                    end_time = course.attendance_end

                if end_time and now_ph.time() > end_time:
                    attendance_record_status = 'late'
            except Exception:
                pass
        
        # Create/update attendance record
        with transaction.atomic():
            attendance_record, created = AttendanceRecord.objects.update_or_create(
                student=student,
                course=course,
                attendance_date=today,
                schedule_day=schedule_day or '',
                defaults={
                    'enrollment': enrollment,
                    'attendance_time': now_ph.time(),
                    'status': attendance_record_status,
                }
            )
            
            # Log the biometric attendance
            logger.info(f"[BIOMETRIC] Student {student.full_name} ({student.id}) marked {attendance_record_status} in {course.code} via fingerprint")
        
        return JsonResponse({
            'success': True,
            'message': f'{student.full_name} marked {attendance_record_status}',
            'student_name': student.full_name,
            'student_id': student.id,
            'student_pk': student.pk,
            'status': attendance_record_status,
            'attendance_time': now_ph.strftime('%H:%M:%S')
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        logger.error(f"Error recording biometric attendance: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'Error: {str(e)}'
        }, status=500)

# ==================== FINGERPRINT DETECTION FROM ESP32 ====================

@csrf_exempt  # Allow POST from ESP32 without CSRF token
@require_http_methods(["POST"])
def fingerprint_detection_view(request):
    """
    Receive fingerprint detection from ESP32 sensor.
    This is called directly by the ESP32 when a fingerprint is detected.
    
    Expected POST data:
    {
        'fingerprint_id': <int>,  # ID from sensor database (1-255), or -1 for unregistered
        'confidence': <int>,
        'timestamp': <int>
    }
    
    The detection is stored temporarily so the instructor's polling endpoint can retrieve it.
    """
    try:
        data = json.loads(request.body)
        fingerprint_id = data.get('fingerprint_id')
        confidence = data.get('confidence', 0)
        
        if fingerprint_id is None:
            return JsonResponse({
                'success': False,
                'error': 'Missing fingerprint_id'
            }, status=400)
        
        logger.info(f"[DETECTION] Fingerprint detected - ID: {fingerprint_id}, Confidence: {confidence}")
        
        # Store detection in cache/session for polling
        # Using Django cache to store temporary detections
        from django.core.cache import cache
        
        # Create a unique key for this detection
        detection_key = f"fingerprint_detection_{fingerprint_id}_{int(timezone.now().timestamp() * 1000)}"
        
        # Store detection data with 30-second expiry
        detection_data = {
            'fingerprint_id': fingerprint_id,
            'confidence': confidence,
            'timestamp': timezone.now().isoformat()
        }
        cache.set(detection_key, detection_data, 30)
        
        # Also maintain a queue of recent detections
        detections_queue_key = "fingerprint_detections_queue"
        queue = cache.get(detections_queue_key, [])
        queue.append({
            'fingerprint_id': fingerprint_id,
            'confidence': confidence,
            'timestamp': timezone.now().isoformat(),
            'key': detection_key
        })
        
        # Keep only last 50 detections
        queue = queue[-50:]
        cache.set(detections_queue_key, queue, 60)  # Cache for 1 minute
        
        logger.info(f"[DETECTION] Stored detection - Queue size: {len(queue)}")
        
        return JsonResponse({
            'success': True,
            'message': 'Fingerprint detection received',
            'fingerprint_id': fingerprint_id
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON'
        }, status=400)
    except Exception as e:
        logger.error(f"Error receiving fingerprint detection: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def instructor_start_biometric_detection_view(request):
    """
    Start biometric fingerprint detection for attendance scanning.
    Called by instructor interface when opening the dual scanner.
    
    Enables the ESP32 fingerprint sensor to detect fingerprints.
    
    POST /api/instructor/attendance/start/
    {
        'course_id': <int>,
        'schedule_id': <str> (optional),
        'session_id': <str> (unique session identifier)
    }
    
    Returns:
    {
        'success': True/False,
        'message': 'Detection started' or error message,
        'session_id': session identifier
    }
    """
    try:
        if not request.user.is_teacher:
            return JsonResponse({
                'success': False,
                'message': 'Only instructors can start detection.'
            }, status=403)
        
        data = json.loads(request.body)
        course_id = data.get('course_id')
        session_id = data.get('session_id', f"session_{timezone.now().timestamp()}")
        
        if not course_id:
            return JsonResponse({
                'success': False,
                'message': 'Missing course_id'
            }, status=400)
        
        # Verify course exists and instructor has access
        from dashboard.models import Course
        try:
            course = Course.objects.get(id=int(course_id))
            if course.instructor != request.user:
                return JsonResponse({
                    'success': False,
                    'message': 'You do not have permission to access this course.'
                }, status=403)
        except (Course.DoesNotExist, ValueError):
            return JsonResponse({
                'success': False,
                'message': 'Course not found'
            }, status=404)
        
        # Enable fingerprint detection on ESP32 via MQTT
        from dashboard.mqtt_client import get_mqtt_client
        mqtt_client = get_mqtt_client()
        
        if mqtt_client and mqtt_client.is_connected:
            # Send detection enable request to ESP32
            detection_request = {
                'action': 'start_detection',
                'mode': 2,  # MODE_ATTENDANCE
                'course_id': course.id,
                'session_id': session_id
            }
            mqtt_client.publish('biometric/esp32/detect/request', detection_request, qos=1)
            logger.info(f"[API] ✓ Fingerprint detection enabled for attendance - Course: {course.code}, Session: {session_id}")
            
            return JsonResponse({
                'success': True,
                'message': 'Fingerprint detection started',
                'session_id': session_id
            })
        else:
            logger.warning("[API] MQTT client not connected - detection could not be started")
            
            return JsonResponse({
                'success': False,
                'message': 'Biometric sensor not connected. Please ensure the ESP32 sensor is online.',
                'error': 'sensor_offline'
            }, status=503)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON'
        }, status=400)
    except Exception as e:
        logger.error(f"Error starting biometric detection: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'Error: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["POST"])
def instructor_stop_biometric_detection_view(request):
    """
    Stop biometric fingerprint detection for attendance scanning.
    Called by instructor when closing the dual scanner.
    
    POST /api/instructor/attendance/stop/
    {
        'course_id': <int>,
        'session_id': <str> (optional)
    }
    
    Returns:
    {
        'success': True/False,
        'message': 'Detection stopped' or error message
    }
    """
    try:
        if not request.user.is_teacher:
            return JsonResponse({
                'success': False,
                'message': 'Only instructors can stop detection.'
            }, status=403)
        
        data = json.loads(request.body)
        course_id = data.get('course_id')
        
        if not course_id:
            return JsonResponse({
                'success': False,
                'message': 'Missing course_id'
            }, status=400)
        
        # Verify course exists
        from dashboard.models import Course
        try:
            course = Course.objects.get(id=int(course_id))
        except (Course.DoesNotExist, ValueError):
            return JsonResponse({
                'success': False,
                'message': 'Course not found'
            }, status=404)
        
        # Disable fingerprint detection on ESP32 via MQTT
        from dashboard.mqtt_client import get_mqtt_client
        mqtt_client = get_mqtt_client()
        
        if mqtt_client and mqtt_client.is_connected:
            # Send detection disable request to ESP32
            detection_request = {
                'action': 'stop_detection',
                'mode': 0  # MODE_IDLE
            }
            mqtt_client.publish('biometric/esp32/detect/request', detection_request, qos=1)
            logger.info(f"[API] ✓ Fingerprint detection disabled - Course: {course.code}")
            
            return JsonResponse({
                'success': True,
                'message': 'Fingerprint detection stopped'
            })
        else:
            # Even if client is not connected, consider it a success (detection is already off)
            return JsonResponse({
                'success': True,
                'message': 'Fingerprint detection stopped'
            })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON'
        }, status=400)
    except Exception as e:
        logger.error(f"Error stopping biometric detection: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'Error: {str(e)}'
        }, status=500)