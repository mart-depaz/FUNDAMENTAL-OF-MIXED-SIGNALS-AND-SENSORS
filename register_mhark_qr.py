#!/usr/bin/env python
"""
Register a new simple ID-based QR code for Mhark Anthony R. Alegre
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
print(f"School ID: {student.school_id}")

# Get his enrollment
enrollment = CourseEnrollment.objects.filter(
    student=student,
    is_active=True
).first()

if enrollment:
    course = enrollment.course
    print(f"Course: {course.code} - {course.name}")
    
    # Create new QR registration with just the school ID
    qr_code_value = student.school_id
    
    # Deactivate old QR if exists
    old_qr = QRCodeRegistration.objects.filter(
        student=student,
        course=course,
        is_active=True
    ).first()
    
    if old_qr:
        old_qr.is_active = False
        old_qr.save()
        print(f"\nDeactivated old QR: {old_qr.qr_code}")
    
    # Create new QR registration
    new_qr, created = QRCodeRegistration.objects.get_or_create(
        student=student,
        course=course,
        qr_code=qr_code_value,
        defaults={'is_active': True}
    )
    
    if created:
        print(f"\n✓ Created new QR registration!")
        print(f"  QR Code: {new_qr.qr_code}")
        print(f"  Active: {new_qr.is_active}")
        print(f"  Registered: {new_qr.created_at}")
    else:
        if not new_qr.is_active:
            new_qr.is_active = True
            new_qr.save()
        print(f"\n✓ QR already exists and is now active!")
        print(f"  QR Code: {new_qr.qr_code}")
        print(f"  Active: {new_qr.is_active}")
else:
    print("Error: No active course enrollment found")

print("\n" + "=" * 70)
print("What to do next:")
print("=" * 70)
print(f"1. Scan your school ID: {student.school_id}")
print(f"2. OR use a barcode/QR generator with the value: {student.school_id}")
print(f"3. Try scanning again in 'Scan Student ID'")
print("=" * 70 + "\n")
