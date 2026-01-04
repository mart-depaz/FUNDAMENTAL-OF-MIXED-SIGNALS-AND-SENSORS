# Biometric Fingerprint Enrollment - Setup & Testing Guide

## 🚨 CRITICAL ISSUE IDENTIFIED

**WiFi Band Mismatch:** Your PC is on **5 GHz** but ESP32 only supports **2.4 GHz**

### Network Status
- **PC WiFi Band:** 5 GHz (802.11ac)
- **ESP32 WiFi Support:** 2.4 GHz only (802.11b/g/n)
- **Network Name:** DE PAZ
- **PC IPv4:** 192.168.1.6
- **ESP32 IPv4:** 192.168.1.10

---

## ✅ Step 1: Fix WiFi Configuration

### Problem
Your router broadcasts "DE PAZ" only on 5 GHz. ESP32 can't connect to 5 GHz, so they can't communicate.

### Solution: Enable Dual-Band WiFi

1. **Access your router admin panel:**
   - Open browser: `http://192.168.1.1` or `http://192.168.0.1`
   - Login with router credentials
   - Look for "WiFi Settings" or "Wireless"

2. **Enable 2.4 GHz Band:**
   - Find WiFi band settings
   - Enable "2.4 GHz" band
   - Set SSID: "DE PAZ" (same as 5 GHz)
   - Set same password: "Blake_2018"
   - Save/Apply settings

3. **Verify both bands are enabled:**
   - Your router should now broadcast:
     - "DE PAZ" on 2.4 GHz (for ESP32)
     - "DE PAZ" on 5 GHz (for your PC)

4. **Optional - Disable band isolation:**
   - Look for "Band Steering" or "WiFi Band Isolation"
   - Disable if available (allows 2.4 GHz and 5 GHz devices to communicate)

---

## ✅ Step 2: Verify System Setup

### Check ESP32
```bash
# Monitor ESP32 serial output
pio device monitor -b 115200
```

Look for:
- ✓ "WiFi Connected" 
- ✓ "IP: 192.168.1.x" (could be .10, .11, etc. - any local IP)
- ✓ "R307 DETECTED"
- ✓ "Web Server started on port 80"

### Check Django Server

1. **Start Django (from FUNDAMENTAL folder):**
```bash
cd "c:\Users\USER\OneDrive\Documents\QR code & Biometric Attendance System\FUNDAMENTAL-OF-MIXED-SIGNALS-AND-SENSORS"
python manage.py runserver 0.0.0.0:8000
```

Expected output:
```
Django version 6.0, using settings 'library_root.settings'
Starting development server at http://0.0.0.0:8000/
```

2. **Test Django in browser:**
   - http://localhost:8000/dashboard/api/health-check/
   - Should return: `{"status": "ok", ...}`

### Test Network Connectivity

```bash
# Run comprehensive network test
cd "c:\Users\USER\OneDrive\Documents\QR code & Biometric Attendance System\FUNDAMENTAL-OF-MIXED-SIGNALS-AND-SENSORS"
python test_biometric_system.py
```

Expected output for properly configured system:
```
✓ ESP32 is REACHABLE
✓ Django is REACHABLE
✓ Enrollment endpoint WORKING
✓✓✓ SYSTEM READY FOR BIOMETRIC ENROLLMENT ✓✓✓
```

---

## ✅ Step 3: Test Fingerprint Enrollment

### Via Web Interface

1. **Open Django Dashboard:**
   - http://localhost:8000/ (or your PC's network address)
   - Login as student

2. **Navigate to "Enroll in Course"**
   - Click blue "Fingerprint" button

3. **Click "Start" to begin enrollment**
   - Follow prompts to place finger on sensor
   - 5 scans required
   - Progress shown as 0% → 100%

### Via Direct API Test

```bash
# Send enrollment request to ESP32
curl -X POST http://192.168.1.10/enroll \
  -H "Content-Type: application/json" \
  -d '{"slot": 1, "template_id": "test_template_001"}'
```

Expected response:
```json
{"success": true, "message": "Enrollment started - waiting for 5 scans"}
```

---

## 📊 System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     WiFi Network (DE PAZ)                    │
│  ┌─────────────────┐          ┌──────────────────┐          │
│  │  ESP32 (2.4GHz) │          │ PC WiFi (5GHz)   │          │
│  │  192.168.1.10   │◄────────►│  192.168.1.6     │          │
│  │  R307 Sensor    │          │  Django Server   │          │
│  │  Web Server:80  │          │  Port 8000       │          │
│  └─────────────────┘          └──────────────────┘          │
│         ▲                               ▲                    │
│         │                               │                    │
│    Fingerprint                    Browser/Requests           │
│    Sensor                                                    │
│    (UART)                                                    │
└─────────────────────────────────────────────────────────────┘

Workflow:
1. Student opens enroll_course.html
2. Clicks "Start" button
3. Frontend calls: POST http://192.168.1.10/enroll
4. ESP32 captures 5 fingerprint scans
5. Shows progress: 0% → 100%
6. Enrollment complete
7. Django updates student record
```

---

## 🔧 Troubleshooting

### "ESP32 NOT REACHABLE" Error
**Cause:** WiFi band mismatch (5 GHz vs 2.4 GHz)
**Fix:** Enable 2.4 GHz band on router (see Step 1)

### "Django NOT REACHABLE" Error  
**Cause:** Django server not running or not on correct port
**Fix:** Start Django with: `python manage.py runserver 0.0.0.0:8000`

### Fingerprint Sensor Not Detected
**Status:** R307 shows "NOT DETECTED"
**Fix:** 
- Check wiring: Violet=5V, Blue=GND, White→GPIO16, Orange→GPIO17
- Verify R307 has power (small red LED should be on)
- Check UART2 baud rate in code (57600)

### Enrollment Gets Stuck
**Cause:** Network timeout waiting for scans
**Fix:**
- Ensure all 5 scans are captured completely
- Check quality feedback (should be 80-100%)
- Retry enrollment if quality is low

### WebSocket Connection Timeout
**Cause:** Real-time updates not reaching frontend
**Fix:** This is optional - enrollment still works without WebSocket
- Django will process updates via HTTP polling as fallback

---

## ✨ Current System Status

| Component | Status | Notes |
|-----------|--------|-------|
| ESP32 Hardware | ✓ | DOIT Devkit V1, 4MB Flash |
| R307 Sensor | ✓ | Detected at 57600 baud |
| WiFi (ESP32) | ✓ | Connected to DE PAZ |
| Web Server (ESP32) | ✓ | Running on port 80 |
| Django Server | ✓ | Running on port 8000 |
| Frontend (HTML) | ✓ | Updated with correct ESP32 IP |
| **Band Mismatch** | ✗ | **WiFi 5GHz/2.4GHz isolation** |
| **Network Routing** | ✗ | **Blocked until WiFi fixed** |

---

## 🎯 Next Steps

1. **ACCESS ROUTER SETTINGS** (most critical)
   - Go to 192.168.1.1 or 192.168.0.1
   - Enable both 2.4 GHz and 5 GHz bands
   - Set both to SSID "DE PAZ"
   - Save and wait 30 seconds for router to restart

2. **RUN TEST SCRIPT**
   ```bash
   python test_biometric_system.py
   ```

3. **TEST ENROLLMENT**
   - Open http://localhost:8000/ in browser
   - Navigate to enroll course
   - Click fingerprint button and follow prompts

4. **VERIFY 5 SCANS**
   - Check serial monitor for scan confirmations
   - All 5 scans should show "success"
   - Quality scores should be 80%+

---

## 📝 Quick Reference

| Item | Value |
|------|-------|
| ESP32 IP | 192.168.1.10 |
| Django IP | 192.168.1.6 |
| Django Port | 8000 |
| ESP32 Web Server | Port 80 |
| WiFi SSID | DE PAZ |
| WiFi Password | Blake_2018 |
| Enrollment Scans | 5 scans required |
| R307 Sensor Baud | 57600 |
| Serial Monitor Baud | 115200 |

---

**Created:** December 25, 2025
**System:** Biometric Fingerprint Enrollment
**Version:** 1.0 (WiFi Band Issue Identified)
