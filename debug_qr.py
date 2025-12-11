#!/usr/bin/env python
"""Debug script to check QR registrations in the database"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'library_root.settings')
django.setup()

from dashboard.models import QRCodeRegistration
from accounts.models import CustomUser

print("=" * 80)
print("ACTIVE QR CODE REGISTRATIONS IN DATABASE")
print("=" * 80)

active_qrs = QRCodeRegistration.objects.filter(is_active=True).select_related('student', 'course')

if active_qrs.exists():
    for idx, qr in enumerate(active_qrs, 1):
        print(f"\n{idx}. QR Registration")
        print(f"   Student: {qr.student.full_name} ({qr.student.school_id})")
        print(f"   Course: {qr.course.code}")
        print(f"   QR Code Value: '{qr.qr_code}'")
        print(f"   QR Code Length: {len(qr.qr_code)} chars")
        print(f"   Active: {qr.is_active}")
        print(f"   Created: {qr.created_at}")
else:
    print("\nNo active QR registrations found!")

print("\n" + "=" * 80)
print("CHECKING IF SCANNED VALUE EXISTS IN DB")
print("=" * 80)

test_qr = "EPIS, CLIFFORD ALEGRIA 166701002@Alipao|4059216"
print(f"\nSearching for: '{test_qr}'")
print(f"Length: {len(test_qr)}")

exact_match = QRCodeRegistration.objects.filter(qr_code=test_qr, is_active=True).first()
if exact_match:
    print(f"✓ FOUND! Student: {exact_match.student.full_name}")
else:
    print(f"✗ NOT FOUND in DB")
    print("\nAll active QR codes in DB:")
    for qr in QRCodeRegistration.objects.filter(is_active=True):
        print(f"  - '{qr.qr_code}'")
        if qr.qr_code == test_qr:
            print(f"    ^ MATCHES!")

print("\n" + "=" * 80)
