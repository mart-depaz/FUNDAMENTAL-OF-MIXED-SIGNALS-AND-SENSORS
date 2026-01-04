import requests
import time

time.sleep(2)  # Give server time to fully start

# Test health check
try:
    resp = requests.get('http://127.0.0.1:8000/dashboard/api/health-check/')
    print(f"✓ Health Check: {resp.status_code}")
    print(f"  Response: {resp.json()}")
except Exception as e:
    print(f"✗ Health Check Error: {e}")

# Test start-enrollment  
try:
    resp = requests.post('http://127.0.0.1:8000/dashboard/api/start-enrollment/', 
                        json={'course_id': 1},
                        headers={'Content-Type': 'application/json'})
    print(f"\n✓ Start Enrollment: {resp.status_code}")
    print(f"  Response: {resp.text[:300]}")
except Exception as e:
    print(f"✗ Start Enrollment Error: {e}")

# Test enrollment-status  
try:
    resp = requests.get('http://127.0.0.1:8000/dashboard/api/enrollment-status/test-enrollment-1/')
    print(f"\n✓ Enrollment Status: {resp.status_code}")
    print(f"  Response: {resp.text[:300]}")
except Exception as e:
    print(f"✗ Enrollment Status Error: {e}")
