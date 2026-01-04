# Test Endpoints

## Check Django Routes

Run this to see all Django URL patterns:

```bash
cd c:\Users\USER\OneDrive\Documents\QR code & Biometric Attendance System\FUNDAMENTAL-OF-MIXED-SIGNALS-AND-SENSORS
python manage.py show_urls | grep fingerprint
```

Expected output should show the full path to the fingerprint-detection endpoint.

## Manual Test: Send Fingerprint Detection from PC

If Django is running on 192.168.1.10:8000, test this from PowerShell:

```powershell
$uri = "http://192.168.1.10:8000/api/fingerprint-detection/"
$body = @{
    fingerprint_id = 42
    confidence = 190
    timestamp = [int][double]::Parse((Get-Date (Get-Date).ToUniversalTime() -UFormat %s))
} | ConvertTo-Json

Invoke-WebRequest -Uri $uri -Method POST -Body $body -ContentType "application/json" -Verbose
```

If that fails, try:
```powershell
$uri = "http://192.168.1.10:8000/dashboard/api/fingerprint-detection/"
```

The one that returns 200-OK with `{"success": true}` is the correct endpoint.

## Test Polling Endpoint

Also test that the polling endpoint works:

```powershell
$uri = "http://192.168.1.10:8000/instructor/biometric-pending/?course_id=1"
Invoke-WebRequest -Uri $uri -Method GET -Verbose
```

Or if that fails:
```powershell
$uri = "http://192.168.1.10:8000/dashboard/instructor/biometric-pending/?course_id=1"
```

## Results

Share the output and I'll update the ESP32 configuration with the correct endpoint.
