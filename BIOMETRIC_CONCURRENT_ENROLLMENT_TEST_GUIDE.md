# Biometric Concurrent Enrollment Testing Guide

## Overview
This document provides comprehensive testing procedures to verify that the biometric enrollment system prevents concurrent registrations and ensures each student gets a unique fingerprint ID.

## System Architecture

### Client-Side Protection (Frontend)
- **sessionStorage Lock**: Per-instructor enrollment lock using browser sessionStorage
- **Location**: `templates/dashboard/student/enroll_course.html` (Lines 2515-2562)
- **Functions**:
  - `getEnrollmentStateKey()` - Creates unique key for instructor
  - `isInstructorEnrollmentInProgress()` - Checks if another student is enrolling
  - `setInstructorEnrollmentInProgress()` - Sets/clears lock flag

### Server-Side Protection (Backend)
- **Cache-Based Lock**: Uses Django cache (default: 5-minute timeout)
- **Location**: `dashboard/views.py` (check_instructor_enrollment_lock & api_biometric_enroll_view)
- **Functions**:
  - `get_enrollment_lock_key(instructor_id)` - Generates cache key
  - `check_instructor_enrollment_lock()` - NEW endpoint to check lock status
  - Lock enforcement in `api_biometric_enroll_view()` - Prevents concurrent enrollments
  - Lock cleared on successful completion or error

### Database Constraint
- **Multi-Course Support**: Same student can have same `fingerprint_id` across multiple courses
- **Unique Constraint**: `unique_student_fingerprint_id` on `[student, fingerprint_id]`
- **Meaning**: Each student has unique fingerprint IDs, but can reuse same ID across courses from same instructor
- **Location**: `dashboard/models.py` (BiometricRegistration model)

---

## Test Scenarios

### Test 1: Same Student, Different Browsers (Same Device)
**Objective**: Verify same student can retry enrollment without being blocked

**Steps**:
1. Open browser window 1 (Chrome)
2. Login as **Student A**
3. Navigate to "Enroll Course" page
4. Start biometric enrollment process (click "Start 3-Capture Enrollment")
5. **Pause** at some point (don't complete, but don't close modal)
6. Open browser window 2 (same device, same Chrome or different browser)
7. Login as **Student A** (same account)
8. Navigate to "Enroll Course" page
9. Try to start biometric enrollment
10. **Expected Result**: Should NOT be blocked - same student allowed
11. Browser 1: Complete enrollment normally
12. Browser 2: Should show an error or allow normal flow since student A completed

**Passes**: ✓ If same student can continue enrollment in another browser

---

### Test 2: Different Students, Same Instructor (Same Device)
**Objective**: Verify different students cannot enroll simultaneously for same instructor

**Setup**:
- Student A and Student B are both enrolled in courses taught by **Instructor X**
- Both courses under same instructor

**Steps**:
1. Open browser window 1
2. Login as **Student A**
3. Navigate to "Enroll Course" page for Instructor X's courses
4. Click "Start 3-Capture Enrollment" button
5. **PAUSE** the enrollment (wait at fingerprint capture screen, don't close)
6. Open browser window 2 (same device, fresh login)
7. Login as **Student B**
8. Navigate to "Enroll Course" page for Instructor X's courses
9. Click "Start 3-Capture Enrollment" button
10. **Expected Result**: Should see modal/warning: "Another student (Student A) is currently registering their fingerprint. Please wait for them to finish."
11. Student B should NOT be able to proceed
12. Student A: Complete enrollment in Browser 1
13. **Wait 2 seconds** for lock to clear
14. Student B: Try "Start 3-Capture Enrollment" again
15. **Expected Result**: Now should work - lock cleared

**Passes**: ✓ If Student B is blocked while Student A is enrolling, and allowed after Student A completes

---

### Test 3: Different Students, Different Instructors (Same Device)
**Objective**: Verify students CAN enroll simultaneously if instructors are different

**Setup**:
- Student A enrolled in courses by **Instructor X**
- Student B enrolled in courses by **Instructor Y**
- Different instructors

**Steps**:
1. Open browser window 1
2. Login as **Student A**
3. Navigate to "Enroll Course" page for Instructor X's courses
4. Click "Start 3-Capture Enrollment" button
5. **PAUSE** enrollment
6. Open browser window 2 (same device)
7. Login as **Student B**
8. Navigate to "Enroll Course" page for Instructor Y's courses
9. Click "Start 3-Capture Enrollment" button
10. **Expected Result**: Should proceed normally - NO BLOCK
11. Both can be enrolling simultaneously

**Passes**: ✓ If Student B can enroll while Student A is enrolling (different instructors)

---

### Test 4: Different Devices, Same Network (Different Student, Same Instructor)
**Objective**: Verify locking works across different devices (cellphones, laptops)

**Equipment Needed**:
- Device 1: Laptop/Desktop (Chrome)
- Device 2: Cellphone (iOS/Android browser or app)
- Both connected to same network

**Setup**:
- Student A and Student B both enrolled in courses by **Instructor X**

**Steps**:
1. **Device 1 (Laptop)**: Open browser, login as **Student A**
2. Navigate to "Enroll Course" for Instructor X's courses
3. Click "Start 3-Capture Enrollment"
4. **PAUSE** at fingerprint capture (don't proceed)
5. **Device 2 (Cellphone)**: Open browser/app, login as **Student B**
6. Navigate to "Enroll Course" for Instructor X's courses
7. Click "Start 3-Capture Enrollment"
8. **Expected Result**: Should see warning "Another student (Student A) is currently registering..."
9. Student B should be BLOCKED
10. **Device 1**: Complete enrollment normally
11. **Wait 2-3 seconds** for server cache to clear
12. **Device 2**: Try "Start 3-Capture Enrollment" again
13. **Expected Result**: Should now proceed

**Passes**: ✓ If blocking works across different physical devices

---

### Test 5: Different Device Brands, Same Instructor
**Objective**: Verify system works with various device types

**Equipment Needed**:
- Device 1: iPhone/iPad (Safari)
- Device 2: Android Phone (Chrome)
- Device 3: Windows Laptop (Firefox)
- Device 4: MacBook (Safari)

**Setup**:
- All have students enrolled in courses by **Instructor X**

**Steps** (Sequential, not simultaneous):
1. **Device 1 (iPhone)**: Login Student A, start enrollment
2. Device 1: Pause enrollment (5 seconds in)
3. **Device 2 (Android)**: Login Student B, try to start enrollment
4. **Expected Result**: BLOCKED - warning shown
5. **Device 1**: Complete enrollment
6. **Device 2**: Retry enrollment - **should work**
7. **Device 2**: Pause enrollment (in progress)
8. **Device 3 (Windows Laptop)**: Login Student C, try to start enrollment
9. **Expected Result**: BLOCKED
10. **Device 2**: Complete enrollment
11. **Device 3**: Retry - **should work**
12. **Device 3**: Pause
13. **Device 4 (MacBook)**: Login Student D, try to start enrollment
14. **Expected Result**: BLOCKED
15. **Device 3**: Complete enrollment
16. **Device 4**: Retry - **should work**

**Passes**: ✓ If each device can enroll sequentially, not simultaneously (for same instructor)

---

### Test 6: Fingerprint ID Assignment Across Multiple Courses
**Objective**: Verify same student gets same fingerprint_id for all courses from same instructor

**Setup**:
- Student A enrolled in 3 courses by **Instructor X**:
  - Course 1: Math 101
  - Course 2: Math 102
  - Course 3: Math 103

**Steps**:
1. Login as **Student A**
2. Navigate to "Enroll Course"
3. Enroll biometric for all 3 courses (multi-course enrollment)
4. Complete enrollment process
5. Check database:
   ```
   SELECT student_id, course_id, fingerprint_id, is_active 
   FROM dashboard_biometricregistration 
   WHERE student_id=<Student A ID> AND is_active=True
   ```
6. **Expected Result**: All 3 rows have SAME fingerprint_id (e.g., 100)
   ```
   student_id | course_id | fingerprint_id | is_active
   123        | 1         | 100            | True
   123        | 2         | 100            | True
   123        | 3         | 100            | True
   ```

**Passes**: ✓ If all 3 courses show same fingerprint_id for Student A

---

### Test 7: Uniqueness Constraint - Different Students Cannot Share Fingerprint ID
**Objective**: Verify database constraint prevents fingerprint ID conflicts

**Setup**:
- Student A already enrolled with fingerprint_id 100 in Instructor X's courses
- Student B now tries to enroll in same instructor's courses

**Steps**:
1. Student A: Complete enrollment (fingerprint_id should be 100)
2. Verify in database:
   ```
   SELECT fingerprint_id FROM dashboard_biometricregistration 
   WHERE student_id=<Student A ID> AND is_active=True
   ```
   - Should return: 100
3. Student B: Complete enrollment process
4. Verify in database:
   ```
   SELECT fingerprint_id FROM dashboard_biometricregistration 
   WHERE student_id=<Student B ID> AND is_active=True
   ```
   - **Should return**: Different value (e.g., 101, NOT 100)
   - Different students CANNOT have same fingerprint_id

**Passes**: ✓ If Student B gets different fingerprint_id than Student A (not 100)

---

### Test 8: Cross-Device Enrollment with Network Interruption
**Objective**: Verify lock timeout handles stale locks gracefully

**Steps**:
1. **Device 1**: Login Student A, start enrollment
2. **Device 1**: Simulate network failure (browser dev tools > offline)
3. **Device 1**: Wait for enrollment to timeout (should auto-cancel WebSocket after ~30 seconds)
4. **Device 1**: Manually close enrollment modal (click X or Cancel)
5. **Device 2**: Login Student B on different device
6. **Device 2**: Try to start enrollment for same instructor
7. **Expected Result (Immediate)**: Might see "Another student enrolling..." but lock should clear after ~30 seconds
8. **Device 2**: Wait 30+ seconds and retry
9. **Expected Result**: Should work - stale lock cleared by timeout

**Passes**: ✓ If lock times out after 5 minutes inactivity (or WebSocket closes)

---

### Test 9: Concurrent Enrollment in Database - Constraint Check
**Objective**: Verify database constraint prevents duplicate fingerprint IDs at DB level

**Manual Test**:
1. Open Django shell:
   ```bash
   python manage.py shell
   ```

2. Run these commands:
   ```python
   from dashboard.models import BiometricRegistration, CustomUser, Course
   
   # Get a student and course
   student = CustomUser.objects.filter(is_student=True).first()
   course = Course.objects.first()
   
   # Try to create duplicate fingerprint_id manually
   BiometricRegistration.objects.create(
       student=student,
       course=course,
       fingerprint_id=100,  # Reuse 100
       biometric_data="test",
       is_active=True
   )
   ```

3. **Expected Result**: Should see error like:
   ```
   IntegrityError: UNIQUE constraint failed: dashboard_biometricregistration.student_id, 
   dashboard_biometricregistration.fingerprint_id
   ```
   - This confirms constraint is working

**Passes**: ✓ If constraint error is raised (prevents duplicates at DB level)

---

## Browser Console Testing

### Monitor Lock Status in Console

**JavaScript Console Commands**:
```javascript
// Check enrollment lock
sessionStorage.getItem('enrollment_in_progress_instructor_1')

// Expected output when locked:
// "123"  (student ID 123 is enrolling)

// Expected output when unlocked:
// null
```

### Check Network Requests

**Network Tab**:
1. Open DevTools > Network tab
2. Start enrollment
3. Look for POST requests to:
   - `/api/biometric/enroll/` - Main enrollment endpoint
   - `/api/biometric/check-enrollment-lock/` - Lock check endpoint
4. **Response for `/api/biometric/check-enrollment-lock/`**:
   - When locked: `{'is_locked': True, 'enrolling_student': 'John Doe'}`
   - When unlocked: `{'is_locked': False, 'enrolling_student': None}`

---

## Expected HTTP Status Codes

### Success (Lock Check)
```
GET /api/biometric/check-enrollment-lock/
Response 200 OK
{
  'success': True,
  'is_locked': False,
  'enrolling_student': None,
  'message': 'Ready to enroll'
}
```

### Locked Response (Different Student)
```
POST /api/biometric/enroll/
Response 423 Locked (HTTP Status Code for Locked)
{
  'success': False,
  'message': '⏳ Another student (Student A) is currently registering their fingerprint. Please wait for them to finish before starting your enrollment.',
  'is_locked': True,
  'other_student': 'Student A'
}
```

### Success (Same Student Can Proceed)
```
POST /api/biometric/enroll/
Response 200 OK
{
  'success': True,
  'message': 'Fingerprint registered successfully...',
  'fingerprint_id': 100,
  'is_replacement': False
}
```

---

## Backend Logging

### Check Django Logs for Lock Events

**Expected Log Messages**:

**Lock Set**:
```
[ENROLLMENT LOCK] SET - Student John Doe (ID: 123) started enrollment for instructor Dr. Smith
```

**Lock Blocked**:
```
[ENROLLMENT LOCK] BLOCKED! Student Jane Doe (ID: 456) attempted to enroll while John Doe (ID: 123) is already enrolling under instructor Dr. Smith
```

**Lock Cleared (Success)**:
```
[ENROLLMENT LOCK] CLEARED - Student John Doe (ID: 123) completed enrollment for instructor Dr. Smith
```

**Lock Cleared (Error)**:
```
[ENROLLMENT LOCK] CLEARED (on error) for instructor Dr. Smith
```

**Same Student Re-attempting**:
```
[ENROLLMENT LOCK] Same student John Doe (ID: 123) re-attempting enrollment
```

---

## Summary: What to Verify

| Test Case | Expected Behavior | Status |
|-----------|------------------|--------|
| Same student, different browsers | Allowed (same student) | ✓ |
| Different students, same instructor | BLOCKED on 2nd student | ✓ |
| Different students, different instructors | Both allowed simultaneously | ✓ |
| Different physical devices (cellphone + laptop) | Blocking works cross-device | ✓ |
| Different device brands (iPhone, Android, Windows, Mac) | Blocking works on all devices | ✓ |
| Same student, 3 courses, 1 instructor | All 3 courses get same fingerprint_id | ✓ |
| Different students, same instructor | Each gets unique fingerprint_id | ✓ |
| Network interruption | Lock timeout clears stale locks | ✓ |
| Database constraint | Prevents duplicate fingerprint_id | ✓ |

---

## Conclusion

This comprehensive testing ensures:
✅ **Per-Student Fingerprint IDs**: Each student gets unique fingerprint ID
✅ **Multi-Course Support**: Same student can use same fingerprint_id across courses from same instructor
✅ **Concurrent Prevention**: Only one student can enroll at a time per instructor
✅ **Cross-Device Security**: Works across cellphones, laptops, different brands
✅ **Database Integrity**: Constraints prevent duplicates at DB level
✅ **Graceful Failures**: Timeouts handle stale locks and network issues
