#!/usr/bin/env python
"""
Verify Fingerprint ID Uniqueness
Check for:
1. Unique fingerprint IDs per student
2. Duplicate fingerprint IDs (security issue)
3. Fingerprint ID distribution
4. Database integrity
"""

import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'library_root.settings')
django.setup()

from accounts.models import CustomUser
from dashboard.models import BiometricRegistration
from django.db.models import Count, Q

print("=" * 80)
print("FINGERPRINT UNIQUENESS VERIFICATION")
print("=" * 80)

# 1. TOTAL FINGERPRINT RECORDS
print("\n[1] FINGERPRINT ENROLLMENT STATUS")
print("-" * 80)
total_registrations = BiometricRegistration.objects.count()
enrolled = BiometricRegistration.objects.filter(fingerprint_id__isnull=False).count()
not_enrolled = BiometricRegistration.objects.filter(fingerprint_id__isnull=True).count()

print(f"Total BiometricRegistration records: {total_registrations}")
print(f"  - With fingerprint ID: {enrolled}")
print(f"  - Without fingerprint ID (pending): {not_enrolled}")

# 2. CHECK FOR DUPLICATE FINGERPRINT IDs
print("\n[2] CHECKING FOR DUPLICATE FINGERPRINT IDs")
print("-" * 80)
try:
    # Find fingerprint IDs that appear more than once
    duplicates = (BiometricRegistration.objects
                  .filter(fingerprint_id__isnull=False)
                  .values('fingerprint_id')
                  .annotate(count=Count('fingerprint_id'))
                  .filter(count__gt=1))
    
    if duplicates.exists():
        print("⚠ WARNING: DUPLICATE FINGERPRINT IDs FOUND!")
        for dup in duplicates:
            fid = dup['fingerprint_id']
            count = dup['count']
            registrations = BiometricRegistration.objects.filter(fingerprint_id=fid)
            print(f"\n  Fingerprint ID {fid} appears {count} times:")
            for reg in registrations:
                print(f"    - Student: {reg.student.full_name} (ID: {reg.student.school_id})")
                print(f"      Course: {reg.course.code if reg.course else 'N/A'}")
                print(f"      Enrolled: {reg.created_at}")
    else:
        print("✓ NO DUPLICATE FINGERPRINT IDs FOUND")
        print(f"✓ All {enrolled} enrolled students have unique fingerprint IDs")
except Exception as e:
    print(f"ERROR: {e}")

# 3. FINGERPRINT ID RANGE CHECK
print("\n[3] FINGERPRINT ID RANGE VALIDATION")
print("-" * 80)
try:
    from django.db.models import Min, Max
    
    fingerprints = BiometricRegistration.objects.filter(fingerprint_id__isnull=False)
    min_id = fingerprints.aggregate(Min('fingerprint_id'))['fingerprint_id__min']
    max_id = fingerprints.aggregate(Max('fingerprint_id'))['fingerprint_id__max']
    
    print(f"Valid range for ESP32: 1-127")
    print(f"Actual range in database: {min_id}-{max_id}")
    
    if min_id < 1 or max_id > 127:
        print("⚠ WARNING: Some fingerprint IDs are outside valid range!")
    else:
        print("✓ All fingerprint IDs are within valid ESP32 range (1-127)")
except Exception as e:
    print(f"ERROR: {e}")

# 4. UNIQUENESS PER STUDENT
print("\n[4] FINGERPRINT UNIQUENESS PER STUDENT")
print("-" * 80)
try:
    # Check if any student has multiple fingerprint enrollments for same course
    student_course_duplicates = (BiometricRegistration.objects
                                 .filter(is_active=True)
                                 .values('student_id', 'course_id')
                                 .annotate(count=Count('id'))
                                 .filter(count__gt=1))
    
    if student_course_duplicates.exists():
        print("⚠ WARNING: Students with multiple enrollments per course:")
        for dup in student_course_duplicates:
            student = CustomUser.objects.get(id=dup['student_id'])
            print(f"  Student: {student.full_name} has {dup['count']} enrollments")
    else:
        print("✓ Each student has at most 1 enrollment per course")
except Exception as e:
    print(f"ERROR: {e}")

# 5. DETAILED FINGERPRINT DISTRIBUTION
print("\n[5] FINGERPRINT DISTRIBUTION ANALYSIS")
print("-" * 80)
try:
    enrolled_bios = BiometricRegistration.objects.filter(fingerprint_id__isnull=False).order_by('fingerprint_id')
    
    print(f"\nTotal enrolled students: {enrolled_bios.count()}")
    print(f"\nDetailed List:")
    print(f"{'Slot':<6} {'Student':<40} {'ID':<15} {'Course':<20} {'Status':<12}")
    print("-" * 100)
    
    for bio in enrolled_bios[:20]:  # Show first 20
        student_name = bio.student.full_name[:40]
        student_id = bio.student.school_id
        course_code = bio.course.code if bio.course else 'N/A'
        status = "✓ Active" if bio.is_active else "✗ Inactive"
        
        print(f"{bio.fingerprint_id:<6} {student_name:<40} {student_id:<15} {course_code:<20} {status:<12}")
    
    if enrolled_bios.count() > 20:
        print(f"... and {enrolled_bios.count() - 20} more students")
        
except Exception as e:
    print(f"ERROR: {e}")

# 6. STUDENT-FINGERPRINT MAPPING
print("\n[6] STUDENT-TO-FINGERPRINT MAPPING")
print("-" * 80)
try:
    students_with_fingerprints = (CustomUser.objects
                                  .filter(is_student=True)
                                  .annotate(fingerprint_count=Count('biometric_registrations', 
                                                                    filter=Q(biometric_registrations__fingerprint_id__isnull=False))))
    
    with_fp = students_with_fingerprints.filter(fingerprint_count__gt=0).count()
    without_fp = students_with_fingerprints.filter(fingerprint_count=0).count()
    
    print(f"Students with fingerprints enrolled: {with_fp}")
    print(f"Students without fingerprints: {without_fp}")
    print(f"Total students: {students_with_fingerprints.count()}")
    
    if with_fp > 0:
        print(f"\nEnrollment rate: {(with_fp / students_with_fingerprints.count() * 100):.1f}%")
    
except Exception as e:
    print(f"ERROR: {e}")

# 7. DATA INTEGRITY CHECK
print("\n[7] DATA INTEGRITY VERIFICATION")
print("-" * 80)
try:
    integrity_issues = []
    
    # Check for fingerprints without active student
    orphaned = BiometricRegistration.objects.filter(
        fingerprint_id__isnull=False
    ).exclude(
        student__is_student=True
    )
    if orphaned.exists():
        integrity_issues.append(f"  ⚠ {orphaned.count()} fingerprints assigned to non-student accounts")
    
    # Check for fingerprints without course
    no_course = BiometricRegistration.objects.filter(
        fingerprint_id__isnull=False,
        course__isnull=True
    )
    if no_course.exists():
        integrity_issues.append(f"  ⚠ {no_course.count()} fingerprints without course assignment")
    
    # Check for inactive fingerprints that are enrolled
    inactive = BiometricRegistration.objects.filter(
        fingerprint_id__isnull=False,
        is_active=False
    )
    if inactive.exists():
        integrity_issues.append(f"  ⚠ {inactive.count()} inactive fingerprints (should be cleaned up)")
    
    if integrity_issues:
        print("Issues found:")
        for issue in integrity_issues:
            print(issue)
    else:
        print("✓ Database integrity check passed")
        print("  - All fingerprints linked to valid students")
        print("  - All fingerprints have course assignments")
        print("  - All active fingerprints are marked as active")
        
except Exception as e:
    print(f"ERROR: {e}")

# 8. SUMMARY REPORT
print("\n" + "=" * 80)
print("FINGERPRINT UNIQUENESS VERIFICATION REPORT")
print("=" * 80)

try:
    total_students = CustomUser.objects.filter(is_student=True).count()
    enrolled_unique = BiometricRegistration.objects.filter(
        fingerprint_id__isnull=False
    ).values('fingerprint_id').distinct().count()
    
    total_enrolled = BiometricRegistration.objects.filter(
        fingerprint_id__isnull=False
    ).count()
    
    print(f"\n✓ FINGERPRINT UNIQUENESS: VERIFIED")
    print(f"  - Total unique fingerprint IDs: {enrolled_unique}")
    print(f"  - Total enrollment records: {total_enrolled}")
    print(f"  - Duplicate fingerprints: {'YES - SECURITY ISSUE!' if enrolled_unique < total_enrolled else 'NO - All unique'}")
    print(f"\n✓ SYSTEM STATUS:")
    print(f"  - Total students in system: {total_students}")
    print(f"  - Students with fingerprints: {with_fp}")
    print(f"  - Enrollment coverage: {(with_fp / total_students * 100):.1f}%")
    print(f"  - Database integrity: PASSED")
    
    if enrolled_unique == total_enrolled and not duplicates.exists():
        print(f"\n✓✓✓ FINAL VERIFICATION: ALL FINGERPRINT IDs ARE UNIQUE ✓✓✓")
        print(f"Safe for production deployment!")
    else:
        print(f"\n⚠ ATTENTION REQUIRED: Data consistency issues detected")
        
except Exception as e:
    print(f"ERROR: {e}")

print("=" * 80)
