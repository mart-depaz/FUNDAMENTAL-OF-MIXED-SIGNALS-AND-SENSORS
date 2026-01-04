# for accounts app urls.py


from django.urls import path
from . import views
from . import admin_views
from . import student_enrollment_api

urlpatterns = [
    path('', views.login_signup_view, name='login_signup'),
    path('logout/', views.logout_view, name='logout'),
    path('reset-password/', views.reset_password_view, name='reset_password'),
    path('approve_teacher/<int:user_id>/', views.approve_teacher, name='approve_teacher'),
    path('api/get-schools/', views.get_schools_by_education_level, name='get_schools'),
    path('api/get-programs/', views.get_programs_by_school, name='get_programs'),
    # Admin routes (custom admin portal - separate from Django admin)
    path('admin-portal/', admin_views.admin_login_signup_view, name='admin_login_signup'),
    path('admin-portal/logout/', admin_views.admin_logout_view, name='admin_logout'),
    
    # Biometric Enrollment APIs (Network-agnostic - works on any WiFi/network)
    path('api/student/enroll/start/', student_enrollment_api.start_fingerprint_enrollment, name='enroll_start'),
    path('api/start-enrollment/', student_enrollment_api.start_enrollment_new, name='start_enrollment_new'),  # NEW ENDPOINT
    path('api/student/enroll/cancel/', student_enrollment_api.cancel_fingerprint_enrollment, name='enroll_cancel'),
    path('api/student/enroll/status/', student_enrollment_api.get_enrollment_status, name='enroll_status'),
    path('api/student/enroll/debug/', student_enrollment_api.debug_enrollment_mappings, name='enroll_debug'),
    path('api/student/attendance/', student_enrollment_api.mark_attendance, name='attendance'),
    path('api/device/status/', student_enrollment_api.get_device_status, name='device_status'),
    path('api/enrollment/webhook/', student_enrollment_api.enrollment_webhook, name='enrollment_webhook'),
    
    # Biometric Attendance Detection APIs (Network-agnostic)
    # NOTE: These are under /accounts/api/... to avoid clashing with dashboard APIs
    # exposed at /api/instructor/attendance/start|stop/.
    path('accounts/api/instructor/attendance/start/', student_enrollment_api.start_attendance_detection, name='attendance_start'),
    path('accounts/api/instructor/attendance/stop/', student_enrollment_api.stop_attendance_detection, name='attendance_stop'),
]