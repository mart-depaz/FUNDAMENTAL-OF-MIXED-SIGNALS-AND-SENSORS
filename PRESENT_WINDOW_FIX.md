# Present Window Attendance Status Fix

## Issue Summary
Students who scanned QR codes **after** the present window was closed were being marked as **PRESENT** instead of **LATE**.

## Root Cause
In [dashboard/views.py](dashboard/views.py) at line ~6602 in the `student_scan_qr_attendance_view()` function, there was a bug:

```python
# BUG: course_end was never defined
if course_end and current_time <= course_end:
    status = 'late'
```

The variable `course_end` was referenced but never initialized, causing the logic to fail silently and default to `'present'` status regardless of whether the present window had expired.

## Changes Made

### 1. **Backend Fix** - [dashboard/views.py](dashboard/views.py#L6570-L6635)

**Issue:** Missing `course_end_time` variable initialization

**Solution:** 
- Added code to get the course end time from either the day-specific schedule or the course-level settings
- Fixed the logic to properly check if attendance is late:
  - If the current time is **within the present duration window** → Mark as `'present'`
  - If the current time is **after the present duration window expires** → Mark as `'late'`
  - The late status is maintained even if the scan happens after the course end time

```python
# Get course end time for today
course_end_time = None
if today_schedule:
    course_end_time = today_schedule.end_time
else:
    course_end_time = course.end_time

# When present window expires, mark as late
if present_duration_minutes and qr_opened_at_dt:
    present_cutoff = qr_opened_at_dt + datetime.timedelta(minutes=int(present_duration_minutes))
    if now_ph <= present_cutoff:
        status = 'present'
    else:
        # After present-window has expired, mark as late
        status = 'late'
```

### 2. **Instructor Notification Update** - [dashboard/views.py](dashboard/views.py#L6687-L6699)

**Improvement:** Notifications now clearly indicate whether student was marked as "present" or "late"

```python
status_text = 'marked as late' if status == 'late' else 'marked as present'
message=f'{student_name} {status_text} for {course.code} - {course.name}'
```

### 3. **API Response Enhancement** - [dashboard/views.py](dashboard/views.py#L6707-L6715)

**Improvement:** Added `is_late` flag to API response for better frontend handling

```python
{
    'success': True,
    'message': f'Attendance marked successfully! Status: {status.capitalize()}',
    'status': status,
    'is_late': status == 'late'
}
```

### 4. **Student QR Scanner UI Update** - [templates/dashboard/student/student_qr_scanner.html](templates/dashboard/student/student_qr_scanner.html#L112-L133)

**Improvement:** Shows different notification style for late attendance

```javascript
const notificationType = data.status === 'late' ? 'warning' : 'success';
const notificationMessage = data.is_late ? 
    `⏰ Marked as Late - ${data.message || 'You scanned after the present window closed.'}` :
    (data.message || 'Attendance marked successfully!');

if (typeof showNotification === 'function') {
    showNotification(notificationMessage, notificationType);
}
```

### 5. **Instructor Dashboard Notification (Already Correct)**

The countdown timer message in [templates/dashboard/instructor/my_classes.html](templates/dashboard/instructor/my_classes.html#L806-L810) was already correct:

```javascript
showNotification('Present window ended — students who scan now will be marked late.', 'error');
```

## How It Works Now

### Present Window Flow:

1. **Instructor opens attendance** and sets a "present window" (e.g., 20 minutes)
2. **QR code is activated** - `qr_code_opened_at` is recorded with current timestamp
3. **Countdown timer starts** - Shows remaining time on instructor's dashboard
4. **Present window expires** after set minutes - Instructor sees notification: "Present window ended — students who scan now will be marked late."

### Student Scanning:

**Within Present Window (0-20 min):**
- ✅ Student scans QR code
- ✅ Marked as **PRESENT**
- ✅ Notification: "Attendance marked successfully! Status: Present"

**After Present Window (20+ min):**
- ✅ Student scans QR code
- ⏰ Marked as **LATE** (was incorrectly marking as PRESENT before fix)
- ⏰ Notification: "⏰ Marked as Late - Attendance marked successfully! Status: Late"

### Instructor Dashboard:

- **Scanned list updates** showing each student's status (present/late)
- **Notifications sync** - Shows "marked as present" or "marked as late" for each student
- **Attendance reports** - Correctly shows present/late counts

## Testing Checklist

- [x] Verify instructor can set present window duration
- [x] Verify countdown timer appears on instructor dashboard
- [x] Verify "present window ended" notification shows on instructor dashboard
- [x] Test student scanning **within** present window → should be marked PRESENT ✅
- [x] Test student scanning **after** present window → should be marked LATE ✅
- [x] Verify notifications show correct status on both sides
- [x] Check attendance reports show correct present/late counts
- [x] Verify course-level and day-specific schedules both work correctly

## Technical Details

**Files Modified:**
1. `dashboard/views.py` - Core logic fix for late attendance detection
2. `templates/dashboard/student/student_qr_scanner.html` - UI improvements for late status

**No Database Migrations Required:**
- All existing fields used
- No new fields added
- Backward compatible with existing data

**Key Datetime Logic:**
- Uses Philippines timezone (Asia/Manila)
- Compares `now_ph` (current time with timezone) against `present_cutoff` (QR opened time + present duration)
- Supports both day-specific and course-level configurations
