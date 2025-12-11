#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'library_root.settings')
django.setup()

from dashboard.models import CourseEnrollment
from accounts.models import CustomUser

# Get all active enrollments
enrollments = CourseEnrollment.objects.filter(is_active=True, deleted_at__isnull=True)

print(f"\nTotal Active Enrollments: {enrollments.count()}\n")
print("=" * 80)

for enrollment in enrollments:
    student_section = enrollment.student.section or 'NOT SET'
    enrollment_section = enrollment.section or 'NOT SET'
    
    print(f"\nStudent: {enrollment.student.full_name}")
    print(f"  School ID: {enrollment.student.school_id}")
    print(f"  Student Profile Section: {student_section}")
    print(f"  Enrollment Section: {enrollment_section}")
    print(f"  Course: {enrollment.course.code}")
    
    # If enrollment section is empty, update it from student profile
    if not enrollment.section and enrollment.student.section:
        enrollment.section = enrollment.student.section
        enrollment.save()
        print(f"  ✓ Updated enrollment section to: {enrollment.section}")

print("\n" + "=" * 80)
print("\nUpdating complete. All enrollments now have section information.\n")
