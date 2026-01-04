#!/usr/bin/env python
import urllib.request
import sys

try:
    url = "http://localhost:8000/dashboard/api/health-check/"
    print(f"Testing connection to: {url}")
    response = urllib.request.urlopen(url, timeout=5)
    data = response.read().decode('utf-8')
    print(f"Status: {response.status}")
    print(f"Response: {data}")
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
