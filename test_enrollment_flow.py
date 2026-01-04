#!/usr/bin/env python3
"""
Test script to verify the biometric enrollment flow is working correctly
"""

import os
import sys
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'library_root.settings')
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

import json
import logging
from django.test import Client
from django.contrib.auth import get_user_model
from dashboard.models import Course, Program, Department, CourseEnrollment, BiometricRegistration
from dashboard.enrollment_state import _enrollment_states, create_enrollment_state

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

User = get_user_model()

def test_enrollment_api():
    """Test the enrollment API endpoint"""
    
    print("\n" + "="*80)
    print("TESTING BIOMETRIC ENROLLMENT FLOW")
    print("="*80 + "\n")
    
    # 1. Create or get test data
    print("[1] Setting up test data...")
    
    # Create department
    dept, _ = Department.objects.get_or_create(
        code='CS',
        defaults={'name': 'Computer Science'}
    )
    print(f"✓ Department: {dept.code}")
    
    # Create program
    program, _ = Program.objects.get_or_create(
        code='BSCS',
        defaults={'name': 'Bachelor of Science in Computer Science', 'department': dept}
    )
    print(f"✓ Program: {program.code}")
    
    # Create course
    course, _ = Course.objects.get_or_create(
        code='CS101',
        defaults={
            'name': 'Introduction to Programming',
            'program': program,
            'year_level': 1,
            'semester': '1st'
        }
    )
    print(f"✓ Course: {course.code}")
    
    # Create test student user
    student_user, _ = User.objects.get_or_create(
        username='teststudent',
        defaults={
            'email': 'teststudent@example.com',
            'full_name': 'Test Student',
            'user_type': 'student',
            'school_id': 'STU001',
            'is_active': True
        }
    )
    print(f"✓ Student: {student_user.full_name} ({student_user.username})")
    
    # Enroll student in course
    enrollment, _ = CourseEnrollment.objects.get_or_create(
        student=student_user,
        course=course,
        defaults={'enrolled_at': django.utils.timezone.now()}
    )
    print(f"✓ Enrollment: {student_user.full_name} -> {course.code}")
    
    print("\n[2] Testing API endpoints...")
    
    # Create test client
    client = Client()
    
    # 2. Test enrollment start API
    print("\n[2a] Testing /api/student/enroll/start/...")
    
    # First login the user
    client.force_login(student_user)
    
    # Make enrollment request
    enrollment_data = {
        'course_id': course.id,
        'student_id': student_user.id
    }
    
    response = client.post(
        '/api/student/enroll/start/',
        data=json.dumps(enrollment_data),
        content_type='application/json'
    )
    
    print(f"  Status: {response.status_code}")
    response_data = json.loads(response.content)
    print(f"  Response: {json.dumps(response_data, indent=2)}")
    
    if response.status_code == 200 and response_data.get('success'):
        enrollment_id = response_data.get('enrollment_id')
        print(f"  ✓ Enrollment ID: {enrollment_id}")
        
        # 3. Verify state was created
        print(f"\n[2b] Checking enrollment state...")
        if enrollment_id in _enrollment_states:
            state = _enrollment_states[enrollment_id]
            print(f"  ✓ State created:")
            print(f"    - Status: {state.get('status')}")
            print(f"    - User ID: {state.get('user_id')}")
            print(f"    - Course ID: {state.get('course_id')}")
            print(f"    - Message: {state.get('message')}")
        else:
            print(f"  ✗ State NOT found for enrollment ID: {enrollment_id}")
            print(f"  Available states: {list(_enrollment_states.keys())}")
        
        # 4. Simulate scan updates
        print(f"\n[2c] Simulating scan update...")
        scan_data = {
            'enrollment_id': enrollment_id,
            'slot': 1,
            'success': True,
            'quality_score': 95,
            'message': 'Scan 1/3 captured'
        }
        
        response = client.post(
            '/api/broadcast-scan-update/',
            data=json.dumps(scan_data),
            content_type='application/json'
        )
        
        print(f"  Status: {response.status_code}")
        response_data = json.loads(response.content)
        print(f"  Response: {response_data}")
        
        if response.status_code == 200:
            print(f"  ✓ Scan update broadcast successful")
        else:
            print(f"  ✗ Scan update failed")
    else:
        print(f"  ✗ API call failed!")
        print(f"  Error: {response_data.get('message')}")
    
    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80 + "\n")

if __name__ == '__main__':
    try:
        test_enrollment_api()
    except Exception as e:
        print(f"\n✗ Error during test: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
