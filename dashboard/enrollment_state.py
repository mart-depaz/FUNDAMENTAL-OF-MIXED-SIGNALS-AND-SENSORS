"""
Centralized Enrollment State Management Module
Single source of truth for all enrollment states used by:
- Polling API (/api/enrollment-status/)
- WebSocket consumers
- MQTT Bridge
- Frontend applications
"""

import logging
from django.utils import timezone

logger = logging.getLogger(__name__)

# ======================== GLOBAL STATE (Single Source of Truth) ========================
_enrollment_states = {}


def create_enrollment_state(enrollment_id, user_id, course_id, template_id=None, is_re_registration=False, old_fingerprint_id=None):
    """
    Create a new enrollment state
    Called when starting a new enrollment session
    """
    if enrollment_id in _enrollment_states:
        logger.warning(f"[STATE] Enrollment {enrollment_id} already exists, overwriting")
    
    state = {
        'status': 'processing',
        'current_scan': 0,
        'progress': 0,
        'message': 'Initializing enrollment...',
        'course_id': course_id,
        'user_id': user_id,
        'created_at': timezone.now().isoformat(),
        'scans': [],
        'is_re_registration': is_re_registration,
        'old_fingerprint_id': old_fingerprint_id,
        'template_id': template_id or enrollment_id  # For MQTT matching
    }
    
    _enrollment_states[enrollment_id] = state
    logger.info(f"[STATE] ✓ Created enrollment state: {enrollment_id}")
    return state


def get_enrollment_state(enrollment_id):
    """Get current enrollment state"""
    if enrollment_id not in _enrollment_states:
        logger.warning(f"[STATE] Enrollment {enrollment_id} not found")
        return None
    
    return _enrollment_states[enrollment_id]


def find_enrollment_id_by_template_id(template_id):
    """Find enrollment_id by template_id"""
    if not template_id:
        return None

    for enrollment_id, state in list(_enrollment_states.items()):
        if state.get('template_id') == template_id:
            return enrollment_id

    return None


def update_enrollment_state(enrollment_id, current_scan=None, progress=None, message=None, status=None, error=None, fingerprint_id=None):
    """
    Update enrollment state - called by MQTT bridge and other handlers
    Used by polling API (/api/enrollment-status/) to serve updates
    """
    if enrollment_id not in _enrollment_states:
        logger.warning(f"[STATE] Attempted to update non-existent enrollment: {enrollment_id}")
        return False
    
    state = _enrollment_states[enrollment_id]
    updated = False
    
    # Update only provided fields
    if current_scan is not None:
        state['current_scan'] = current_scan
        updated = True
        logger.debug(f"[STATE] Updated {enrollment_id}: current_scan={current_scan}")
    
    if progress is not None:
        state['progress'] = progress
        updated = True
        logger.debug(f"[STATE] Updated {enrollment_id}: progress={progress}%")
    
    if message is not None:
        state['message'] = message
        updated = True
        logger.debug(f"[STATE] Updated {enrollment_id}: message={message}")
    
    if status is not None:
        state['status'] = status
        updated = True
        logger.debug(f"[STATE] Updated {enrollment_id}: status={status}")
    
    if error is not None:
        state['error'] = error
        updated = True
        logger.error(f"[STATE] Updated {enrollment_id}: error={error}")

    if fingerprint_id is not None:
        state['fingerprint_id'] = fingerprint_id
        updated = True
        logger.debug(f"[STATE] Updated {enrollment_id}: fingerprint_id={fingerprint_id}")
    
    if updated:
        logger.info(f"[STATE] ✓ Enrollment state updated: {enrollment_id} -> scan={state.get('current_scan')}, progress={state.get('progress')}%, status={state.get('status')}")
    
    return True


def delete_enrollment_state(enrollment_id):
    """Delete enrollment state when enrollment is complete"""
    if enrollment_id in _enrollment_states:
        del _enrollment_states[enrollment_id]
        logger.info(f"[STATE] ✓ Deleted enrollment state: {enrollment_id}")
        return True
    return False


def cleanup_old_enrollments(user_id, course_id):
    """
    Remove old enrollments for the same user/course
    Called when user re-registers to prevent state collision
    """
    removed = []
    for eid, state in list(_enrollment_states.items()):
        if state.get('user_id') == user_id and state.get('course_id') == course_id:
            del _enrollment_states[eid]
            removed.append(eid)
            logger.info(f"[STATE] ✓ Cleaned up old enrollment for re-registration: {eid}")
    
    if removed:
        logger.info(f"[STATE] Removed {len(removed)} old enrollments: {removed}")
    
    return removed


def get_all_states():
    """Get all enrollment states (for debugging)"""
    return _enrollment_states.copy()
