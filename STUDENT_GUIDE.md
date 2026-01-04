# Biometric Registration - Student Guide

## Complete Workflow

### Step 1: Start Enrollment
1. Go to **Enroll in Course** page in student dashboard
2. Enter the **Course Enrollment Code** (8 characters)
3. Click **Verify Code**
4. Select the **Instructor** from the list
5. Click the **Biometric** button (purple fingerprint icon)

### Step 2: Biometric Registration Modal
The modal will show:
- **Fingerprint icon** (center)
- **Status**: "Ready to Scan"
- **Count**: "0/5"
- **START button** (purple)
- **CANCEL button**

### Step 3: Click START Button
1. Click the **START** button
2. Status changes to: "Detecting finger... (40s)"
3. Button becomes disabled (processing)
4. Fingerprint icon pulses blue

### Step 4: Place Your Finger
**IMMEDIATELY place your finger on the R307 sensor**
- Press finger **firmly**
- Cover **entire sensor area**
- Keep finger **still**
- Don't move your finger while scanning

### Step 5: Detection & Success
When finger is detected (usually 1-3 seconds):
- Icon changes to ✓ **green checkmark**
- Status shows: "Fingerprint captured"
- Quality score displays (e.g., "Quality: 92%")
- Progress bar advances (20% → 40% → 60% → 80% → 100%)

### Step 6: Repeat for 5 Scans
- **Scan 1/5**: First fingerprint
- **Scan 2/5**: Second fingerprint  
- **Scan 3/5**: Verification of scans 1-2
- **Scan 4/5**: Verification scan
- **Scan 5/5**: Final verification

**Remove your finger between each scan**

### Step 7: Completion
After all 5 scans:
- Icon shows ✓ **green check circle**
- Status: "Enrollment Successful!"
- Message: "Fingerprint enrolled in X course(s)"
- Modal closes automatically after 2 seconds

---

## What If Something Goes Wrong?

### Timeout (No Finger Detected)
**After 40 seconds with no finger:**
- Icon shows ⏱ **yellow exclamation**
- Status: "Please try again"
- Button shows: **"Retry Scan X"**

**Solutions**:
1. Click "Retry Scan X" to try again
2. Clean the sensor with soft cloth
3. Try different finger
4. Press finger more firmly on sensor
5. Check if sensor LED is glowing

### Connection Error
**If "Cannot reach ESP32 at 192.168.1.10"**:
1. Make sure ESP32 device is powered on
2. Check network connectivity
3. Verify you're on the same WiFi network
4. Check ESP32 IP address is correct

### Quality Issues
**If quality score is very low (below 50%)**:
1. Try a different finger
2. Clean sensor with soft cloth
3. Make sure finger isn't too dry or too wet
4. Try different hand position

---

## Progress Tracking

### Visual Indicators

**During Detection**:
```
[Icon: Blue pulsing fingerprint 💙]
[Status: Detecting finger... (35s)]
[Progress bar: Growing]
```

**On Success**:
```
[Icon: Green checkmark ✓]
[Status: Fingerprint captured]
[Subtitle: Quality: 92%]
[Progress: 20% → 40% → 60% → 80% → 100%]
```

**On Timeout**:
```
[Icon: Yellow exclamation ⏱]
[Status: Please try again]
[Button: Retry Scan 2]
```

---

## Tips for Best Results

✓ **DO**:
- Press finger firmly on entire sensor area
- Keep finger still while scanning
- Use dry, clean fingers
- Try different fingers if one doesn't work
- Make sure sensor LED is glowing

✗ **DON'T**:
- Move your finger while scanning
- Use very wet fingers
- Use very dry/calloused fingers
- Rush the process
- Click multiple times on the button

---

## Q&A

**Q: How long do I have to place my finger?**
A: You have 40 seconds from when you click START to place your finger on the sensor.

**Q: What if I make a mistake on a scan?**
A: Click the "Retry Scan X" button to try that scan again.

**Q: Can I use the same finger for all 5 scans?**
A: Yes, use the same finger for all 5 scans for consistency.

**Q: What if my finger is very dry?**
A: Try moistening your finger slightly or using a different finger.

**Q: Why does it take 5 scans?**
A: 5 scans ensure high accuracy and prevent false matches for attendance.

**Q: Can I cancel the enrollment?**
A: Yes, click the CANCEL button or close the modal to stop the process.

**Q: What if enrollment fails?**
A: You'll see an error message. Contact your instructor or IT support.

---

## Technical Details

### ESP32 Device
- **IP Address**: 192.168.1.10
- **Port**: 80 (HTTP)
- **Endpoint**: `/enroll` (POST)
- **Sensor**: R307 Fingerprint Module

### Polling Details
- **Frequency**: Every 100ms (10 times per second)
- **Timeout**: 40 seconds per scan
- **Quality Score**: 0-100%
- **Total Scans**: 5

### Device Configuration
- **GPIO16**: RX (input from R307)
- **GPIO17**: TX (output to R307)
- **Baud Rate**: 57600
- **Protocol**: Serial UART

---

**Last Updated**: December 25, 2025
**Status**: ✅ Ready for Use
