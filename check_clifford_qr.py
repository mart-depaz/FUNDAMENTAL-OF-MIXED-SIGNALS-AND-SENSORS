#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'library_root.settings')
django.setup()

from accounts.models import CustomUser
from dashboard.models import QRCodeRegistration

# Find Clifford
student = CustomUser.objects.filter(full_name__icontains='Clifford').first()

if student:
    print(f"\nStudent: {student.full_name}")
    print(f"School ID: {student.school_id}")
    
    # Get all QR registrations (active and inactive)
    qrs = QRCodeRegistration.objects.filter(student=student)
    print(f"\nTotal QR Records: {qrs.count()}")
    
    for qr in qrs:
        status = "✓ ACTIVE" if qr.is_active else "✗ INACTIVE"
        print(f"  {status}: {qr.qr_code}")
else:
    print("Clifford not found")
