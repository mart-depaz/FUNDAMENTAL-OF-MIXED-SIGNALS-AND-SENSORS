#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'library_root.settings')
django.setup()

from dashboard.models import CourseEnrollment

# Get all active enrollments
enrollments = CourseEnrollment.objects.filter(is_active=True, deleted_at__isnull=True)

print(f"\nPopulating Course Information for {enrollments.count()} Enrollments\n")
print("=" * 100)

for enrollment in enrollments:
    old_code = enrollment.course_code
    old_name = enrollment.course_name
    
    # Update with course information
    enrollment.course_code = enrollment.course.code
    enrollment.course_name = enrollment.course.name
    enrollment.save()
    
    print(f"\nStudent: {enrollment.student.full_name}")
    print(f"  School ID: {enrollment.student.school_id}")
    print(f"  Section: {enrollment.section}")
    print(f"  Course Code: {enrollment.course_code}")
    print(f"  Subject/Course Name: {enrollment.course_name}")

print("\n" + "=" * 100)
print(f"✓ Successfully updated {enrollments.count()} enrollments with course information.\n")
