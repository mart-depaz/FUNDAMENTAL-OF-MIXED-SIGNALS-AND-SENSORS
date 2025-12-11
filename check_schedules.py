#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'library_root.settings')
django.setup()

from dashboard.models import CourseSchedule, Course

# Check course 73
course = Course.objects.get(id=73)
print(f"\nCourse: {course.code} - {course.name}")
print(f"Instructor: {course.instructor.full_name if course.instructor else 'None'}")

# Get all schedules for this course
schedules = CourseSchedule.objects.filter(course=course)
print(f"\nTotal Schedules for Course 73: {schedules.count()}\n")

if schedules.exists():
    for schedule in schedules:
        print(f"Schedule ID: {schedule.id}")
        print(f"  Day: {schedule.day}")
        print(f"  Time: {schedule.start_time} - {schedule.end_time}")
        print()
else:
    print("NO SCHEDULES FOUND for this course!")
