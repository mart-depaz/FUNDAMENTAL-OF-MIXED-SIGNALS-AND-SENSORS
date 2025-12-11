#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'library_root.settings')
django.setup()

from dashboard.models import Course
from accounts.models import CustomUser

# Check if course 73 exists
course = Course.objects.filter(id=73).first()
if course:
    print(f"✓ Course 73 found: {course.code} - {course.name}")
    print(f"  Instructor: {course.instructor.full_name if course.instructor else 'None'}")
    print(f"  Instructor ID: {course.instructor.id if course.instructor else 'None'}")
else:
    print("✗ Course 73 NOT found")

# Check who you are logged in as
instructor = CustomUser.objects.filter(full_name__icontains='levi').first()
if instructor:
    print(f"\nLogged in as: {instructor.full_name} (ID: {instructor.id})")
    
    # Check if this instructor has any courses
    courses = Course.objects.filter(instructor=instructor)
    print(f"Your courses: {courses.count()}")
    for c in courses:
        print(f"  - {c.id}: {c.code} - {c.name}")
