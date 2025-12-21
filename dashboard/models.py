# dashboard/models.py
from django.db import models
from django.db.models import Q
from accounts.models import CustomUser

class Department(models.Model):
    """Model for departments/colleges"""
    name = models.CharField(max_length=200, help_text="Department/College name (e.g., College of Engineering)")
    code = models.CharField(max_length=20, blank=True, null=True, help_text="Department code (e.g., COE, CAS, CBME)")
    icon = models.ImageField(upload_to='department_icons/', blank=True, null=True, help_text="Icon/picture for department folder")
    school_name = models.CharField(max_length=200, blank=True, null=True, help_text="School name - departments are separated by school")
    education_level = models.CharField(
        max_length=20,
        choices=[
            ('high_senior', 'High/Senior High'),
            ('university_college', 'University/College')
        ],
        default='university_college'
    )
    is_active = models.BooleanField(default=True)
    deleted_at = models.DateTimeField(null=True, blank=True, help_text="Soft delete timestamp - item will be permanently deleted after 30 days")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Department'
        verbose_name_plural = 'Departments'
        # Only enforce uniqueness when code is not None
        constraints = [
            models.UniqueConstraint(fields=['code', 'school_name'], condition=models.Q(code__isnull=False), name='unique_code_per_school'),
            models.UniqueConstraint(fields=['name', 'school_name'], name='unique_name_per_school')
        ]

    def __str__(self):
        if self.code:
            return f"{self.code} - {self.name}"
        return self.name

class Program(models.Model):
    """Model for university/college programs (e.g., BSCpE, BSEE)"""
    code = models.CharField(max_length=20, help_text="Program code (e.g., BSCpE, BSEE)")
    name = models.CharField(max_length=200, help_text="Full program name (e.g., Bachelor of Science in Computer Engineering)")
    department = models.CharField(max_length=200, default='', help_text="Parent Department / College (e.g., College of Engineering)")
    department_code = models.CharField(max_length=20, blank=True, null=True, help_text="Department code for quick reference")
    icon = models.ImageField(upload_to='program_icons/', blank=True, null=True, help_text="Icon/picture for program folder")
    school_name = models.CharField(max_length=200, blank=True, null=True, help_text="School name - programs are separated by school")
    education_level = models.CharField(
        max_length=20,
        choices=[
            ('high_senior', 'High/Senior High'),
            ('university_college', 'University/College')
        ],
        default='university_college'
    )
    is_active = models.BooleanField(default=True)
    deleted_at = models.DateTimeField(null=True, blank=True, help_text="Soft delete timestamp - item will be permanently deleted after 30 days")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['code']
        verbose_name = 'Program'
        verbose_name_plural = 'Programs'

    def __str__(self):
        return f"{self.code} - {self.name}"

class AdminNotification(models.Model):
    """Notifications for admins (e.g., new user signups)"""
    NOTIFICATION_TYPES = [
        ('new_teacher_signup', 'New Teacher Signup'),
        ('new_student_signup', 'New Student Signup'),
        ('teacher_approval_request', 'Teacher Approval Request'),
        ('system_alert', 'System Alert'),
        ('course_added', 'Course Added'),
    ]
    
    admin = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='notifications', limit_choices_to={'is_admin': True})
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    related_user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True, related_name='related_notifications')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.admin.full_name or self.admin.username}"

class UserNotification(models.Model):
    """General notifications for all users (instructors, students, admins)"""
    NOTIFICATION_TYPES = [
        ('course_assigned', 'Course Assigned'),
        ('course_updated', 'Course Updated'),
        ('attendance_reminder', 'Attendance Reminder'),
        ('system_alert', 'System Alert'),
        ('account_approved', 'Account Approved'),
        ('account_rejected', 'Account Rejected'),
        ('welcome', 'Welcome Message'),
        ('student_enrolled', 'Student Enrolled'),
        ('upcoming_class', 'Upcoming Class'),
        ('attendance_marked', 'Attendance Marked'),
        ('attendance_control_updated', 'Attendance Control Updated'),
        ('student_dropped', 'Student Dropped'),
        ('course_added', 'Course Added'),
        ('general', 'General Notification'),
    ]
    
    CATEGORY_CHOICES = [
        ('system', 'System'),
        ('enrollment', 'Enrollment'),
        ('course', 'Course'),
        ('account', 'Account'),
        ('general', 'General'),
    ]
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='user_notifications')
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES, default='general')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='general', help_text="Category for organizing notifications")
    title = models.CharField(max_length=200)
    message = models.TextField()
    related_course = models.ForeignKey('Course', on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    related_user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True, related_name='related_user_notifications')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.user.full_name or self.user.username}"

class UserTemporaryPassword(models.Model):
    """Store temporary passwords for users created by admins"""
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='temporary_password_record')
    password = models.CharField(max_length=255, help_text="Temporary password (stored in plain text for document generation)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_used = models.BooleanField(default=False, help_text="Set to True when user changes their password")
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'User Temporary Password'
        verbose_name_plural = 'User Temporary Passwords'
    
    def __str__(self):
        return f"Temporary password for {self.user.full_name or self.user.username}"

class UserCustomPassword(models.Model):
    """Store custom passwords for users in plain text for display purposes"""
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='custom_password_record')
    password = models.CharField(max_length=255, help_text="Custom password (stored in plain text for display)")
    old_password = models.CharField(max_length=255, blank=True, null=True, help_text="Previous custom password (for tracking password history)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'User Custom Password'
        verbose_name_plural = 'User Custom Passwords'
    
    def __str__(self):
        return f"Custom password for {self.user.full_name or self.user.username}"

class Course(models.Model):
    """Model for courses/subjects that students can enroll in"""
    SEMESTER_CHOICES = [
        ('1st', '1st Semester'),
        ('2nd', '2nd Semester'),
        ('summer', 'Summer'),
    ]
    
    # Course identification
    code = models.CharField(max_length=50, help_text="Course code (e.g., CS 101, MATH 203)")
    name = models.CharField(max_length=200, help_text="Course name (e.g., Introduction to Computer Science)")
    
    # Program and level information
    program = models.ForeignKey(Program, on_delete=models.SET_NULL, null=True, blank=True, related_name='courses', help_text="Program this course belongs to (optional)")
    year_level = models.IntegerField(help_text="Year level this course is for (1, 2, 3, 4, etc.)")
    section = models.CharField(max_length=50, help_text="Section (e.g., A, B, 1, 2)")
    semester = models.CharField(max_length=20, choices=SEMESTER_CHOICES, default='1st', help_text="Semester")
    school_year = models.CharField(max_length=20, blank=True, null=True, help_text="School year (e.g., 2024-2025)")
    
    # Instructor and schedule
    instructor = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='taught_courses', limit_choices_to={'is_teacher': True}, help_text="Instructor/Teacher")
    room = models.CharField(max_length=100, blank=True, null=True, help_text="Room/Location (e.g., Bldg A, Rm 302, Online/Zoom)")
    
    # Schedule details
    days = models.CharField(max_length=50, help_text="Days of the week (e.g., Mon,Wed,Fri or Tue,Thu)")
    start_time = models.TimeField(help_text="Class start time")
    end_time = models.TimeField(help_text="Class end time")
    
    # Attendance window (set by instructor)
    attendance_start = models.TimeField(blank=True, null=True, help_text="Attendance check-in start time (set by instructor)")
    attendance_end = models.TimeField(blank=True, null=True, help_text="Attendance check-in end time (set by instructor)")
    
    # Course color for timetable display
    color = models.CharField(max_length=7, default='#3C4770', help_text="Color code for timetable display (hex format)")
    
    # Enrollment code for students to enroll
    enrollment_code = models.CharField(max_length=20, unique=True, blank=True, null=True, help_text="Unique enrollment code for students to enroll in this course")
    
    # Enrollment status control
    enrollment_status = models.CharField(
        max_length=20,
        choices=[
            ('open', 'Open for Enrollment'),
            ('closed', 'Closed Enrollment'),
        ],
        default='open',
        help_text="Enrollment status - controls whether students can enroll using the enrollment code"
    )
    
    # Metadata
    school_name = models.CharField(max_length=200, blank=True, null=True, help_text="School name")
    is_active = models.BooleanField(default=True)
    deleted_at = models.DateTimeField(null=True, blank=True, help_text="Soft delete timestamp - item will be permanently deleted after 30 days")
    is_archived = models.BooleanField(default=False, help_text="Archive flag - for storing completed sessions")
    
    # Attendance control
    attendance_status = models.CharField(
        max_length=20,
        choices=[
            ('automatic', 'Automatic (Based on Attendance Window)'),
            ('closed', 'Closed Attendance'),
            ('open', 'Open Attendance'),
            ('stopped', 'Stop Attendance'),
        ],
        default='automatic',
        help_text="Current attendance status for the course"
    )
    qr_code = models.CharField(max_length=100, unique=True, blank=True, null=True, help_text="Unique QR code for this course section")
    # Present-duration in minutes: number of minutes after QR/session open that counts as 'present'
    attendance_present_duration = models.IntegerField(null=True, blank=True, help_text="Number of minutes counted as 'present' from session open (instructor-set)")
    # Timestamp when QR/session was opened (used with present-duration)
    qr_code_opened_at = models.DateTimeField(null=True, blank=True, help_text="Timestamp when the QR/session was opened by the instructor")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        """Generate enrollment code and QR code if not set"""
        import random
        import string
        import hashlib
        from datetime import datetime
        
        if not self.enrollment_code:
            # Generate a unique 8-character code
            while True:
                code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
                if not Course.objects.filter(enrollment_code=code).exists():
                    self.enrollment_code = code
                    break
        
        # Save first to get the ID if it's a new course
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Generate QR code after save (so we have an ID)
        if not self.qr_code:
            # Generate a unique QR code based on course ID, code, section, and instructor
            qr_data = f"{self.id}_{self.code}_{self.section}_{self.instructor_id if self.instructor_id else 'none'}_{datetime.now().timestamp()}"
            qr_hash = hashlib.sha256(qr_data.encode()).hexdigest()[:16].upper()
            # Ensure uniqueness (exclude current course from check)
            max_attempts = 10
            attempts = 0
            while Course.objects.filter(qr_code=qr_hash).exclude(id=self.id).exists() and attempts < max_attempts:
                qr_hash = hashlib.sha256(f"{qr_data}_{random.randint(1000, 9999)}".encode()).hexdigest()[:16].upper()
                attempts += 1
            self.qr_code = qr_hash
            # Save again to store the QR code (only if it was generated)
            if self.qr_code:
                super().save(update_fields=['qr_code'])
    
    class Meta:
        ordering = ['program', 'year_level', 'code']
        verbose_name = 'Course'
        verbose_name_plural = 'Courses'
        unique_together = [['program', 'year_level', 'section', 'code', 'semester', 'school_year']]
    
    def __str__(self):
        program_code = self.program.code if self.program else 'N/A'
        return f"{self.code} - {self.name} ({program_code} {self.year_level}{self.section}, {self.semester})"
    
    def get_schedules(self):
        """Get all schedules for this course, or return default schedule if none exist"""
        schedules = self.course_schedules.all().order_by('day_order')
        if schedules.exists():
            return schedules
        # Return default schedule if no day-specific schedules exist
        return None

class CourseSchedule(models.Model):
    """Model for day-specific course schedules"""
    DAY_CHOICES = [
        ('Mon', 'Monday'),
        ('Tue', 'Tuesday'),
        ('Wed', 'Wednesday'),
        ('Thu', 'Thursday'),
        ('Fri', 'Friday'),
        ('Sat', 'Saturday'),
        ('Sun', 'Sunday'),
    ]
    
    DAY_ORDER = {
        'Mon': 1,
        'Tue': 2,
        'Wed': 3,
        'Thu': 4,
        'Fri': 5,
        'Sat': 6,
        'Sun': 7,
    }
    
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='course_schedules', help_text="Course this schedule belongs to")
    day = models.CharField(max_length=10, choices=DAY_CHOICES, help_text="Day of the week")
    start_time = models.TimeField(help_text="Class start time for this day")
    end_time = models.TimeField(help_text="Class end time for this day")
    room = models.CharField(max_length=100, blank=True, null=True, help_text="Room/Location for this day (optional, overrides course room)")
    attendance_start = models.TimeField(blank=True, null=True, help_text="Attendance check-in start time for this day (optional, overrides course attendance_start)")
    attendance_end = models.TimeField(blank=True, null=True, help_text="Attendance check-in end time for this day (optional, overrides course attendance_end)")
    day_order = models.IntegerField(default=0, help_text="Order for sorting days")
    qr_code = models.CharField(max_length=100, unique=True, blank=True, null=True, help_text="Unique QR code for this specific day schedule")
    qr_code_date = models.DateField(blank=True, null=True, help_text="Date when QR code was generated for this day")
    # Present-duration overrides course-level setting for this specific day schedule
    attendance_present_duration = models.IntegerField(null=True, blank=True, help_text="Number of minutes counted as 'present' from session open for this day (overrides course-level)")
    # Timestamp when the QR/session was opened for this specific schedule
    qr_code_opened_at = models.DateTimeField(null=True, blank=True, help_text="Timestamp when the QR/session was opened for this schedule")
    attendance_status = models.CharField(
        max_length=20,
        choices=[
            ('automatic', 'Automatic (Based on Attendance Window)'),
            ('closed', 'Closed Attendance'),
            ('open', 'Open Attendance'),
            ('stopped', 'Stop Attendance'),
            ('postponed', 'Postponed'),
        ],
        default='automatic',
        blank=True,
        null=True,
        help_text="Attendance status for this specific day schedule (overrides course-level status if set)"
    )
    
    class Meta:
        ordering = ['day_order', 'start_time']
        verbose_name = 'Course Schedule'
        verbose_name_plural = 'Course Schedules'
        unique_together = [['course', 'day']]
    
    def __str__(self):
        return f"{self.course.code} - {self.get_day_display()} ({self.start_time} - {self.end_time})"
    
    def save(self, *args, **kwargs):
        # Auto-set day_order based on day
        self.day_order = self.DAY_ORDER.get(self.day, 0)
        super().save(*args, **kwargs)

class CourseEnrollment(models.Model):
    """Model for tracking student enrollments in courses"""
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments', help_text="Course the student is enrolling in")
    student = models.ForeignKey('accounts.CustomUser', on_delete=models.CASCADE, related_name='course_enrollments', limit_choices_to={'is_student': True}, help_text="Student enrolling in the course")
    
    # Student information at time of enrollment
    full_name = models.CharField(max_length=90, help_text="Student's full name")
    year_level = models.IntegerField(help_text="Student's year level")
    section = models.CharField(max_length=50, help_text="Student's section")
    email = models.EmailField(help_text="Student's school email")
    student_id_number = models.CharField(max_length=50, help_text="Student's ID number")
    
    # Course information at time of enrollment
    course_code = models.CharField(max_length=50, blank=True, help_text="Course code (e.g., CpE - 123)")
    course_name = models.CharField(max_length=200, blank=True, help_text="Course name/subject (e.g., Fundamental of Mixed Signals and Sensors)")
    course_section = models.CharField(max_length=50, blank=True, help_text="Course section (e.g., A, B, 1, 2 - which section of the course the student is in)")
    
    # Enrollment metadata
    enrolled_at = models.DateTimeField(auto_now_add=True, help_text="When the student enrolled")
    is_active = models.BooleanField(default=True, help_text="Whether the enrollment is active")
    deleted_at = models.DateTimeField(null=True, blank=True, help_text="Soft delete timestamp - item will be permanently deleted after 30 days")
    
    class Meta:
        ordering = ['-enrolled_at']
        verbose_name = 'Course Enrollment'
        verbose_name_plural = 'Course Enrollments'
        unique_together = [['course', 'student']]  # Prevent duplicate enrollments
    
    def __str__(self):
        return f"{self.student.full_name or self.student.username} enrolled in {self.course.code} - {self.course.name}"

class AttendanceRecord(models.Model):
    """Model for tracking student attendance in courses"""
    STATUS_CHOICES = [
        ('present', 'Present'),
        ('late', 'Late'),
        ('absent', 'Absent'),
        ('postponed', 'Postponed'),
    ]
    
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='attendance_records', help_text="Course for this attendance record")
    student = models.ForeignKey('accounts.CustomUser', on_delete=models.CASCADE, related_name='attendance_records', limit_choices_to={'is_student': True}, help_text="Student who attended")
    enrollment = models.ForeignKey(CourseEnrollment, on_delete=models.SET_NULL, null=True, blank=True, related_name='attendance_records', help_text="Enrollment record (preserved when enrollment is dropped)")
    
    # Attendance details
    attendance_date = models.DateField(help_text="Date of attendance")
    attendance_time = models.TimeField(null=True, blank=True, help_text="Time when attendance was recorded (null for absent records)")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='present', help_text="Attendance status")
    schedule_day = models.CharField(max_length=10, blank=True, null=True, help_text="Day of the week for this attendance (Mon, Tue, Wed, etc.) - allows multiple attendance records per day for different schedules")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-attendance_date', '-attendance_time']
        verbose_name = 'Attendance Record'
        verbose_name_plural = 'Attendance Records'
        unique_together = [['course', 'student', 'attendance_date', 'schedule_day']]  # One attendance per student per course per day per schedule
    
    def __str__(self):
        return f"{self.student.full_name or self.student.username} - {self.course.code} - {self.attendance_date}"


class QRCodeRegistration(models.Model):
    """
    Model to store QR code registrations for students in courses.
    Allows instructors to register/assign QR codes to students for attendance scanning.
    """
    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='qr_registrations', help_text="Student who owns this QR code")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='qr_registrations', help_text="Course this QR code is registered for")
    qr_code = models.CharField(max_length=500, help_text="QR code value/ID (can be school ID, UUID, or custom value)")
    registered_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='qr_registrations_created', help_text="Instructor who registered this QR code")
    is_active = models.BooleanField(default=True, help_text="Whether this QR code registration is active")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'QR Code Registration'
        verbose_name_plural = 'QR Code Registrations'
        # Removed unique_together to allow same student to register QR in multiple courses
        # unique_together = [['student', 'course']]  # REMOVED - prevents cross-course registration
        constraints = [
            # One QR code per student per course (this is the per-course uniqueness)
            models.UniqueConstraint(
                fields=['student', 'course'],
                name='uq_student_per_course',
                condition=Q(is_active=True)
            ),
            # Ensure no two active registrations share the same qr_code within a course
            models.UniqueConstraint(
                fields=['qr_code','course'],
                name='uq_active_qr_code_per_course',
                condition=Q(is_active=True)
            )
        ]
        indexes = [
            # NOTE: Removed global index on qr_code to allow same QR across courses
            # models.Index(fields=['qr_code']),  # REMOVED - was causing global unique constraint
            models.Index(fields=['course', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.student.full_name} - {self.course.code} - {self.qr_code[:20]}"


class InstructorRegistrationStatus(models.Model):
    """Track whether an instructor has enabled registration for their courses"""
    instructor = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='registration_status')
    is_registration_enabled = models.BooleanField(default=False)
    enabled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Instructor Registration Status'
        verbose_name_plural = 'Instructor Registration Statuses'
    
    def __str__(self):
        return f"{self.instructor.full_name} - {'Enabled' if self.is_registration_enabled else 'Disabled'}"


class BiometricRegistration(models.Model):
    """
    Model to store biometric (fingerprint) registrations for students in courses.
    Allows students to register their biometric data for attendance scanning.
    """
    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='biometric_registrations', help_text="Student who owns this biometric data")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='biometric_registrations', help_text="Course this biometric is registered for")
    biometric_data = models.TextField(help_text="Encrypted biometric data (fingerprint template)")
    biometric_type = models.CharField(max_length=50, default='fingerprint', help_text="Type of biometric (e.g., fingerprint, face)")
    fingerprint_id = models.IntegerField(null=True, blank=True, help_text="Unique fingerprint ID assigned by the Arduino R307 sensor")
    is_active = models.BooleanField(default=True, help_text="Whether this biometric registration is active")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Biometric Registration'
        verbose_name_plural = 'Biometric Registrations'
        unique_together = [['student', 'course']]  # One biometric per student per course
        indexes = [
            models.Index(fields=['course', 'is_active']),
            models.Index(fields=['student', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.student.full_name} - {self.course.code} - {self.biometric_type}"

