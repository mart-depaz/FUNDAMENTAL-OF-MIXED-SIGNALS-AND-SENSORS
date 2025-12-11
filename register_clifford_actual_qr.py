#!/usr/bin/env python
"""
Register Clifford's actual QR code (the one he scans) to his account
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'library_root.settings')
django.setup()

from accounts.models import CustomUser
from dashboard.models import QRCodeRegistration, CourseEnrollment

# Get Clifford
student = CustomUser.objects.get(full_name__icontains='Clifford')
print(f"\nStudent: {student.full_name}")
print(f"School ID: {student.school_id}")

# The QR code Clifford scans
qr_code_value = "EPIS, CLIFFORD ALEGRIA 166701002@Alipao|4059216"

# Get his course enrollment
enrollment = CourseEnrollment.objects.filter(
    student=student,
    is_active=True
).first()

if enrollment:
    course = enrollment.course
    print(f"Course: {course.code} - {course.name}")
    
    # Delete the old simple ID-based QR (2023-01310)
    old_qr = QRCodeRegistration.objects.filter(
        student=student,
        is_active=True
    ).first()
    
    if old_qr:
        print(f"\nDeleting old QR: {old_qr.qr_code}")
        old_qr.delete()
        print("✓ Deleted")
    
    # Register the new QR code
    new_qr = QRCodeRegistration.objects.create(
        student=student,
        course=course,
        qr_code=qr_code_value,
        is_active=True
    )
    
    print(f"\n✓ NEW QR Code Registered!")
    print(f"  QR Code: {new_qr.qr_code}")
    print(f"  Student: {new_qr.student.full_name} ({new_qr.student.school_id})")
    print(f"  Course: {new_qr.course.code}")
    print(f"  Active: {new_qr.is_active}")
    print(f"  Created: {new_qr.created_at}")
    
    print("\n" + "=" * 70)
    print("HOW IT WORKS NOW:")
    print("=" * 70)
    print(f"1. When you scan: EPIS, CLIFFORD ALEGRIA 166701002@Alipao|4059216")
    print(f"2. System extracts: 166701002 (the numeric ID)")
    print(f"3. System finds your QR in database (contains 166701002)")
    print(f"4. System identifies YOU: {student.full_name} ({student.school_id})")
    print(f"5. System marks you PRESENT")
    print("=" * 70 + "\n")
else:
    print("\nError: No active course enrollment found")
