"""
Biometric utility functions for fingerprint registration and verification.
Handles encryption/decryption of biometric data and database operations.
"""

import hashlib
import hmac
import os
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

# Configuration
BIOMETRIC_ENCRYPTION_KEY = getattr(settings, 'BIOMETRIC_ENCRYPTION_KEY', 'default-insecure-key')
BIOMETRIC_ALGORITHM = 'sha256'


def encrypt_biometric_data(biometric_template):
    """
    Encrypt biometric fingerprint template using HMAC.
    
    Args:
        biometric_template (str): Raw fingerprint template or ID from ESP32
        
    Returns:
        str: Encrypted/hashed biometric data
    """
    try:
        if not biometric_template:
            logger.error("Biometric template is empty")
            return None
        
        # Create HMAC signature of the biometric data
        signature = hmac.new(
            BIOMETRIC_ENCRYPTION_KEY.encode('utf-8'),
            biometric_template.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        # Return combination of original + signature for verification
        encrypted = f"{biometric_template}:{signature}"
        logger.info(f"Encrypted biometric data (first 32 chars): {encrypted[:32]}...")
        return encrypted
    except Exception as e:
        logger.error(f"Error encrypting biometric data: {str(e)}")
        return None


def verify_biometric_match(stored_template, new_template):
    """
    Verify if two biometric templates match.
    
    Args:
        stored_template (str): Stored encrypted biometric data
        new_template (str): New biometric template to verify
        
    Returns:
        bool: True if templates match, False otherwise
    """
    try:
        if not stored_template or not new_template:
            logger.warning("Invalid biometric templates for comparison")
            return False
        
        # Extract original template and signature
        if ':' not in stored_template:
            logger.warning("Invalid stored template format")
            return False
        
        stored_original, stored_signature = stored_template.rsplit(':', 1)
        
        # Create signature for new template using same key
        new_signature = hmac.new(
            BIOMETRIC_ENCRYPTION_KEY.encode('utf-8'),
            new_template.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        # Compare templates and signatures using constant-time comparison
        # to prevent timing attacks
        template_match = hmac.compare_digest(stored_original, new_template)
        signature_match = hmac.compare_digest(stored_signature, new_signature)
        
        match = template_match and signature_match
        logger.info(f"Biometric verification: template_match={template_match}, signature_match={signature_match}, result={match}")
        return match
    except Exception as e:
        logger.error(f"Error verifying biometric data: {str(e)}")
        return False


def generate_biometric_id():
    """
    Generate a unique biometric enrollment ID for ESP32 fingerprint sensor.
    
    Returns:
        int: Enrollment ID (1-127, reserved 0 for deletions, 127 for special use)
    """
    import random
    # ESP32 fingerprint sensor typically supports IDs 1-127
    return random.randint(1, 126)


def format_biometric_response(success, message, enrollment_id=None, template=None):
    """
    Format standardized response for biometric operations.
    
    Returns:
        dict: Formatted response
    """
    response = {
        'success': success,
        'message': message,
        'timestamp': None,
    }
    
    if enrollment_id is not None:
        response['enrollment_id'] = enrollment_id
    
    if template is not None:
        response['template'] = template
    
    from django.utils import timezone
    response['timestamp'] = timezone.now().isoformat()
    
    return response


def enroll_fingerprint_r307(device_ip, finger_id, enrollment_attempts=5):
    """
    Enroll a fingerprint into the R307 module with multiple confirmations.
    
    Args:
        device_ip (str): IP address of the ESP32 with R307 module (e.g., 192.168.1.26)
        finger_id (int): Finger ID (1-127) for enrollment
        enrollment_attempts (int): Number of confirmations needed (default: 5)
        
    Returns:
        dict: Enrollment result with status and biometric template
    """
    import requests
    
    try:
        logger.info(f"Starting fingerprint enrollment for ID {finger_id} on device {device_ip}")
        
        # Check if fingerprint already exists
        check_url = f"http://{device_ip}/check_fingerprint/{finger_id}"
        check_response = requests.get(check_url, timeout=10)
        
        if check_response.status_code == 200:
            check_data = check_response.json()
            if check_data.get('exists', False):
                logger.warning(f"Fingerprint ID {finger_id} already exists on device")
                return {
                    'success': False,
                    'message': f'Fingerprint ID {finger_id} already exists. Please try a different finger.',
                    'enrollment_id': finger_id,
                    'is_duplicate': True
                }
        
        # Start enrollment process
        enrollment_results = []
        
        for attempt in range(1, enrollment_attempts + 1):
            logger.info(f"Enrollment attempt {attempt}/{enrollment_attempts}")
            
            # Send enrollment request to device
            enroll_url = f"http://{device_ip}/enroll_fingerprint"
            enroll_data = {
                'finger_id': finger_id,
                'attempt': attempt,
                'total_attempts': enrollment_attempts
            }
            
            try:
                response = requests.post(enroll_url, json=enroll_data, timeout=30)
                
                if response.status_code == 200:
                    result = response.json()
                    
                    if result.get('success', False):
                        template = result.get('template', '')
                        enrollment_results.append({
                            'attempt': attempt,
                            'success': True,
                            'template': template,
                            'quality': result.get('quality_score', 0),
                            'message': result.get('message', f'Enrollment attempt {attempt} successful')
                        })
                        logger.info(f"Enrollment attempt {attempt} successful")
                    else:
                        enrollment_results.append({
                            'attempt': attempt,
                            'success': False,
                            'message': result.get('message', f'Enrollment attempt {attempt} failed'),
                            'error': result.get('error', 'Unknown error')
                        })
                        logger.warning(f"Enrollment attempt {attempt} failed: {result.get('message')}")
                else:
                    enrollment_results.append({
                        'attempt': attempt,
                        'success': False,
                        'message': f'Device returned status {response.status_code}',
                        'error': response.text
                    })
                    logger.error(f"Device error on attempt {attempt}: {response.status_code}")
                    
            except requests.Timeout:
                enrollment_results.append({
                    'attempt': attempt,
                    'success': False,
                    'message': f'Request timeout on attempt {attempt}',
                    'error': 'Connection timeout'
                })
                logger.error(f"Timeout on enrollment attempt {attempt}")
            except requests.RequestException as e:
                enrollment_results.append({
                    'attempt': attempt,
                    'success': False,
                    'message': f'Communication error on attempt {attempt}',
                    'error': str(e)
                })
                logger.error(f"Communication error on attempt {attempt}: {str(e)}")
        
        # Check if we have enough successful enrollments
        successful_enrollments = [r for r in enrollment_results if r.get('success', False)]
        
        if len(successful_enrollments) >= 3:  # At least 3 out of 5 successful
            logger.info(f"Fingerprint enrollment successful: {len(successful_enrollments)}/{enrollment_attempts} confirmations")
            
            # Get the final template from the most recent successful attempt
            final_template = successful_enrollments[-1].get('template', '')
            encrypted_template = encrypt_biometric_data(final_template)
            
            return {
                'success': True,
                'message': f'Fingerprint enrolled successfully with {len(successful_enrollments)} confirmations',
                'enrollment_id': finger_id,
                'confirmations': len(successful_enrollments),
                'total_attempts': enrollment_attempts,
                'template': encrypted_template,
                'details': enrollment_results,
                'quality_score': sum(r.get('quality', 0) for r in successful_enrollments) / len(successful_enrollments)
            }
        else:
            logger.error(f"Fingerprint enrollment failed: Only {len(successful_enrollments)}/{enrollment_attempts} confirmations")
            return {
                'success': False,
                'message': f'Fingerprint enrollment failed. Only {len(successful_enrollments)} out of {enrollment_attempts} confirmations successful. Please try again.',
                'enrollment_id': finger_id,
                'confirmations': len(successful_enrollments),
                'total_attempts': enrollment_attempts,
                'details': enrollment_results,
                'error': 'Insufficient confirmations'
            }
            
    except Exception as e:
        logger.error(f"Error in fingerprint enrollment: {str(e)}")
        return {
            'success': False,
            'message': f'Error during fingerprint enrollment: {str(e)}',
            'enrollment_id': finger_id,
            'error': str(e)
        }


def check_fingerprint_uniqueness(biometric_template, course_id, exclude_student_id=None):
    """
    Check if fingerprint is unique ONLY within the specific course.
    Student can have the same fingerprint in different courses.
    
    Args:
        biometric_template (str): Encrypted biometric template
        course_id (int): Course ID to check against
        exclude_student_id (int): Student ID to exclude from uniqueness check (own fingerprint)
        
    Returns:
        dict: Uniqueness check result
    """
    from dashboard.models import BiometricRegistration
    
    try:
        # Check if any other student has this fingerprint in THIS SPECIFIC COURSE ONLY
        # This allows the same fingerprint to be used in different courses
        existing = BiometricRegistration.objects.filter(
            course_id=course_id,
            is_active=True
        )
        
        if exclude_student_id:
            existing = existing.exclude(student_id=exclude_student_id)
        
        for record in existing:
            if verify_biometric_match(record.biometric_data, biometric_template):
                logger.warning(f"Fingerprint duplicate detected in course {course_id}")
                return {
                    'is_unique': False,
                    'message': f'This fingerprint is already registered by another student in this course.',
                    'duplicate_student_id': record.student_id,
                    'course_id': course_id
                }
        
        logger.info(f"Fingerprint is unique for course {course_id}")
        return {
            'is_unique': True,
            'message': 'Fingerprint is unique in this course.',
            'course_id': course_id
        }
        
    except Exception as e:
        logger.error(f"Error checking fingerprint uniqueness: {str(e)}")
        return {
            'is_unique': None,
            'message': f'Error checking uniqueness: {str(e)}',
            'error': str(e)
        }
