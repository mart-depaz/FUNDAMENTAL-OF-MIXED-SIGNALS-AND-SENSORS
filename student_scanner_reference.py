#!/usr/bin/env python
"""
Student Scanner Reference - shows which students are registered in which courses with their QR codes
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'library_root.settings')
django.setup()

from accounts.models import CustomUser
from dashboard.models import CourseEnrollment, QRCodeRegistration, Course

print("\n" + "=" * 120)
print("STUDENT QR SCANNER REFERENCE GUIDE")
print("=" * 120)
print("\nWhen scanning a QR code, here's who will be marked present:\n")

# Get all active courses
courses = Course.objects.filter(is_active=True, deleted_at__isnull=True).distinct()

for course in courses:
    print(f"\n{'─' * 120}")
    print(f"COURSE: {course.code} - {course.name}")
    print(f"Instructor: {course.instructor.full_name if course.instructor else 'N/A'}")
    print(f"{'─' * 120}")
    
    # Get all enrollments for this course
    enrollments = CourseEnrollment.objects.filter(
        course=course,
        is_active=True,
        deleted_at__isnull=True
    ).select_related('student').order_by('student__full_name')
    
    if not enrollments.exists():
        print("No enrolled students")
        continue
    
    print(f"\nEnrolled Students:")
    for enrollment in enrollments:
        student = enrollment.student
        section = enrollment.section or student.section or 'N/A'
        year = enrollment.year_level or student.year_level or 'N/A'
        
        # Get QR registration for this course
        qr_reg = QRCodeRegistration.objects.filter(
            student=student,
            course=course,
            is_active=True
        ).first()
        
        qr_status = "✓ REGISTERED" if qr_reg else "✗ NOT REGISTERED"
        
        print(f"\n  {enrollment.id:3d}. {student.full_name}")
        print(f"       School ID: {student.school_id}")
        print(f"       Section: {section} | Year: {year}")
        print(f"       QR Status: {qr_status}", end="")
        
        if qr_reg:
            qr_code_display = qr_reg.qr_code
            if len(qr_code_display) > 60:
                qr_code_display = qr_reg.qr_code[:60] + "..."
            print(f"\n       QR Code: {qr_code_display}")
        else:
            print()

print("\n" + "=" * 120)
print("SCANNING INSTRUCTIONS:")
print("=" * 120)
print("""
1. When you scan a QR code, the system will:
   - Extract the student ID from the QR content
   - Find the registered QR for that student
   - Mark that student as PRESENT
   
2. QR codes can contain any information - what matters is which student they're registered to
   - For example: Mhark's QR contains "EPIS, CLIFFORD..." but marks Mhark present
   
3. Each student can only have ONE QR per course
   - If you try to register a QR already used by another student, it will be rejected
   
4. To see who will be marked present when you scan:
   - Check the student's QR Code value above
   - When you scan that QR, that student gets marked present
""")
print("=" * 120 + "\n")
