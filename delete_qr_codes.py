#!/usr/bin/env python
"""
Delete QR codes with personal information for Eren, Mhark, and John Mart
Keep only ID-based QR codes
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'library_root.settings')
django.setup()

from dashboard.models import QRCodeRegistration
from accounts.models import CustomUser

# Find and delete QR codes for Eren, Mhark, and John Mart
students_to_clear = ['EREN H. YEAGER', 'Mhark Anthony R. Alegre', 'JOHN MART E. DE PAZ']

print("\nDeleting QR Codes with Personal Information")
print("=" * 70)

for student_name in students_to_clear:
    try:
        student = CustomUser.objects.get(full_name=student_name)
        qr = QRCodeRegistration.objects.filter(student=student, is_active=True).first()
        if qr:
            qr_code_value = qr.qr_code
            qr.is_active = False
            qr.save()
            print(f"\n✓ Deleted QR for {student_name}")
            print(f"  Previous QR: {qr_code_value}")
    except CustomUser.DoesNotExist:
        print(f"✗ Student {student_name} not found")

print("\n" + "=" * 70)
print("\nRemaining Active QR Codes:")
print("=" * 70)
qrs = QRCodeRegistration.objects.filter(is_active=True)
for qr in qrs:
    print(f"{qr.student.full_name} ({qr.student.school_id}): {qr.qr_code}")

print("\n" + "=" * 70)
print(f"Total Active QR Codes: {QRCodeRegistration.objects.filter(is_active=True).count()}")
print("=" * 70 + "\n")
