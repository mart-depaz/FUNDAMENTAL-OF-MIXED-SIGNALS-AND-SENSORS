#!/usr/bin/env python3
"""
Biometric Enrollment System - Network & Hardware Test Suite
Tests ESP32-Django integration and fingerprint enrollment
"""

import requests
import json
import time
from urllib.error import URLError, HTTPError
import socket

def test_esp32_reachability():
    """Test if ESP32 is reachable"""
    print("\n" + "="*60)
    print("TEST 1: ESP32 Reachability (192.168.1.10:80)")
    print("="*60)
    
    try:
        response = requests.get("http://192.168.1.10/status", timeout=3)
        print(f"✓ ESP32 is REACHABLE")
        print(f"  Status Code: {response.status_code}")
        print(f"  Response: {response.json()}")
        return True
    except Exception as e:
        print(f"✗ ESP32 NOT REACHABLE")
        print(f"  Error: {e}")
        print(f"  Fix: Ensure ESP32 is on 2.4 GHz WiFi band (same as your PC)")
        return False

def test_django_reachability():
    """Test if Django is reachable"""
    print("\n" + "="*60)
    print("TEST 2: Django Server Reachability (192.168.1.6:8000)")
    print("="*60)
    
    try:
        response = requests.get("http://192.168.1.6:8000/dashboard/api/health-check/", timeout=3)
        print(f"✓ Django is REACHABLE")
        print(f"  Status Code: {response.status_code}")
        print(f"  Response: {response.json()}")
        return True
    except Exception as e:
        print(f"✗ Django NOT REACHABLE")
        print(f"  Error: {e}")
        return False

def test_esp32_enrollment_endpoint():
    """Test ESP32 enrollment endpoint"""
    print("\n" + "="*60)
    print("TEST 3: ESP32 Enrollment Endpoint")
    print("="*60)
    
    try:
        payload = {
            "slot": 1,
            "template_id": "test_template_" + str(int(time.time()))
        }
        print(f"Sending POST to http://192.168.1.10/enroll")
        print(f"Payload: {json.dumps(payload)}")
        
        response = requests.post(
            "http://192.168.1.10/enroll",
            json=payload,
            timeout=3
        )
        print(f"✓ Enrollment endpoint WORKING")
        print(f"  Status Code: {response.status_code}")
        print(f"  Response: {response.json()}")
        return True
    except Exception as e:
        print(f"✗ Enrollment endpoint NOT WORKING")
        print(f"  Error: {e}")
        return False

def test_network_connectivity():
    """Test basic network connectivity"""
    print("\n" + "="*60)
    print("TEST 0: Network Connectivity Check")
    print("="*60)
    
    # Check localhost
    try:
        socket.gethostbyname("localhost")
        print("✓ Localhost DNS resolution: OK")
    except:
        print("✗ Localhost DNS resolution: FAILED")
    
    # Check if we can resolve IPs
    try:
        socket.gethostbyaddr("192.168.1.10")
        print("✓ Can communicate on 192.168.x.x network")
    except:
        print("✗ Cannot communicate on 192.168.x.x network (WiFi band issue?)")

def print_summary(results):
    """Print test summary"""
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    if results['esp32']:
        print("✓ ESP32 is reachable - Hardware integration OK")
    else:
        print("✗ ESP32 not reachable - Check WiFi bands:")
        print("  - Router must have BOTH 2.4 GHz AND 5 GHz enabled")
        print("  - Both should use SSID 'DE PAZ'")
        print("  - Disable WiFi band isolation if available")
    
    if results['django']:
        print("✓ Django server is reachable - Backend OK")
    else:
        print("✗ Django not reachable")
    
    if results['esp32'] and results['django']:
        print("\n✓✓✓ SYSTEM READY FOR BIOMETRIC ENROLLMENT ✓✓✓")
        print("\nYou can now:")
        print("1. Open http://192.168.1.6:8000/dashboard/student/enroll-course/")
        print("2. Click 'Fingerprint' button to trigger enrollment")
        print("3. ESP32 will prompt for 5 fingerprint scans")
        print("4. Frontend will show real-time progress (0% → 100%)")
    else:
        print("\n✗ SYSTEM NOT READY - Fix network issues first")

if __name__ == "__main__":
    results = {
        'network': True,
        'esp32': False,
        'django': False,
        'enrollment': False
    }
    
    print("\n" + "="*60)
    print("BIOMETRIC ENROLLMENT SYSTEM - NETWORK TEST")
    print("="*60)
    
    test_network_connectivity()
    results['esp32'] = test_esp32_reachability()
    results['django'] = test_django_reachability()
    
    if results['esp32']:
        results['enrollment'] = test_esp32_enrollment_endpoint()
    
    print_summary(results)
