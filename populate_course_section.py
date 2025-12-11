#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'library_root.settings')
django.setup()

from dashboard.models import CourseEnrollment

# Get all active enrollments
enrollments = CourseEnrollment.objects.filter(is_active=True, deleted_at__isnull=True)

print(f"\nPopulating Course Section for {enrollments.count()} Enrollments\n")
print("=" * 100)

for enrollment in enrollments:
    # Update with course section information
    enrollment.course_section = enrollment.course.section
    enrollment.save()
    
    print(f"\nStudent: {enrollment.student.full_name}")
    print(f"  School ID: {enrollment.student.school_id}")
    print(f"  Student Section: {enrollment.section}")
    print(f"  Course: {enrollment.course_code} - {enrollment.course_name}")
    print(f"  Course Section: {enrollment.course_section}")

print("\n" + "=" * 100)
print(f"✓ Successfully updated {enrollments.count()} enrollments with course section information.\n")
