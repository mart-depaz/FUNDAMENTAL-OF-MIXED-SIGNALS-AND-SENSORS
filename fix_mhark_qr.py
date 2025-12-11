#!/usr/bin/env python
"""
Fix Mhark's QR registration - replace with correct school ID
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'library_root.settings')
django.setup()

from dashboard.models import QRCodeRegistration, Course, CourseEnrollment
from accounts.models import CustomUser

# Get Mhark
student = CustomUser.objects.get(full_name__icontains='Mhark')
print(f"\nStudent: {student.full_name}")
print(f"Correct School ID: {student.school_id}")

# Delete old incorrect QR
old_qr = QRCodeRegistration.objects.filter(student=student).first()
if old_qr:
    print(f"\nDeleting old incorrect QR:")
    print(f"  Old QR: {old_qr.qr_code}")
    old_qr.delete()
    print(f"  ✓ Deleted")

# Get his course enrollment
enrollment = CourseEnrollment.objects.filter(
    student=student,
    is_active=True
).first()

if enrollment:
    course = enrollment.course
    print(f"\nCourse: {course.code} - {course.name}")
    
    # Create NEW QR registration with CORRECT school ID
    new_qr = QRCodeRegistration.objects.create(
        student=student,
        course=course,
        qr_code=student.school_id,  # Use actual school ID
        is_active=True
    )
    
    print(f"\n✓ Created NEW correct QR registration!")
    print(f"  New QR Code: {new_qr.qr_code}")
    print(f"  Active: {new_qr.is_active}")
    print(f"  Registered: {new_qr.created_at}")
else:
    print("\nError: No active course enrollment found")

print("\n" + "=" * 70)
print("NEXT STEPS:")
print("=" * 70)
print(f"1. Your NEW QR Code is: {student.school_id}")
print(f"2. Scan this ID (or create a barcode/QR with {student.school_id})")
print(f"3. Try scanning in 'Scan Student ID' again")
print("=" * 70 + "\n")
