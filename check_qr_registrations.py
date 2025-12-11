#!/usr/bin/env python
"""
Diagnostic script to check what QR codes are registered in the database.
Run with: python manage.py shell < check_qr_registrations.py
Or: python manage.py shell
>>> exec(open('check_qr_registrations.py').read())
"""

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
print("ALL STUDENTS")
print("=" * 80)

students = CustomUser.objects.filter(is_student=True)
if students.exists():
    for idx, student in enumerate(students[:10], 1):  # Show first 10
        print(f"\n{idx}. Student")
        print(f"   Name: {student.full_name}")
        print(f"   Username: {student.username}")
        print(f"   School ID: {student.school_id}")
        print(f"   ID Field: {student.id}")
else:
    print("\nNo students found!")

print("\n" + "=" * 80)
