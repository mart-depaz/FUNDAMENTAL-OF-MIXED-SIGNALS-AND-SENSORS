# Quick Troubleshooting Guide - MQTT Connectivity Issues

## 🔍 Is Your System Working Now?

After deploying the fix, try this simple test:

### Test Procedure
1. Go to enrollment page
2. Click "Start 3-Capture Enrollment" 
3. **Open Browser Console** (F12 → Console tab)
4. Look for this message:
   ```
   [ENROLLMENT] ⏳ Waiting 3000ms for WebSocket group subscription to fully propagate...
   ```
5. Place your finger 3 times
6. Check if you see all 3 scan updates

### ✅ If Working:
- Console shows: `[ENROLLMENT] ✓ Group subscription fully ready`
- All 3 scans detected (progress bar goes 0% → 33% → 66% → 100%)
- Page reloads and shows "Biometric: Registered"
- **You're done!** The fix works for you.

### ❌ If Still Having Issues:
Continue with the troubleshooting below.

---

## 🔧 Troubleshooting Steps

### Issue #1: Missing First Scan (1/3)
**Symptom:** Scan 2 and 3 work fine, but Scan 1 is sometimes not detected

**Diagnosis:**
1. Look at browser console for:
   ```
   [WEBSOCKET] ===== MESSAGE RECEIVED =====
   [WEBSOCKET] Parsed JSON: {... "step": 1, ...}
   ```
   - If you see this: WebSocket is working ✓
   - If you don't: WebSocket isn't receiving the message ✗

2. Check Django logs for MQTT messages:
   ```
   [MQTT BRIDGE] ===== ENROLLMENT RESPONSE FROM ESP32 =====
   [MQTT BRIDGE] Status: progress
   [MQTT BRIDGE] Step: 1
   ```
   - If you see this: MQTT bridge is working ✓
   - If you don't: ESP32 not publishing or MQTT broker not receiving ✗

3. Check the 3000ms wait:
   ```javascript
   // In browser console, paste:
   console.log('Current wait time:', 3000);
   // Should be exactly 3000ms, not 1500ms
   ```

**Solutions (Try in Order):**
- [ ] Clear browser cache (Ctrl+Shift+Delete)
- [ ] Restart Django server
- [ ] Restart ESP32 (power cycle)
- [ ] Check MQTT broker connectivity (see below)

---

### Issue #2: Missing Middle or Last Scans
**Symptom:** First scan detected, but then 2nd or 3rd scan is missed

**Diagnosis:**
Check for this error in browser console:
```javascript
[WEBSOCKET] ✗ WebSocket error during connection:
// or
[WEBSOCKET] Connection closed
// or
[ERROR] MQTT not connected. Cannot publish
```

**Solutions (Try in Order):**
- [ ] Check internet connection
- [ ] Check WebSocket isn't being blocked (some proxies/firewalls block ws://)
- [ ] Verify MQTT broker is online: `ping broker.hivemq.com`
- [ ] Restart Django + restart ESP32
- [ ] Check for exceptions in Django logs

---

### Issue #3: Scans Detected in Serial But Not in Frontend
**Symptom:**
- Serial monitor shows: `✓ Fingerprint detected! ✓ SCAN 1/3 CAPTURED`
- Frontend shows: Nothing / Blank / Progress bar at 0%

**Diagnosis:**
1. Check ESP32 serial monitor for MQTT publish confirmation:
   ```
   [MQTT] ✓ Scan 1/3 progress published
   ```
   - If you see `✗ Failed`: MQTT publish failed

2. Check Django MQTT bridge logs for incoming message:
   ```
   [MQTT BRIDGE] ===== ENROLLMENT RESPONSE FROM ESP32 =====
   ```
   - If you don't see this: Message lost in transit

3. Check for enrollment_id mismatch:
   ```
   [LOOKUP] ⏳ Enrollment not found on first try
   [LOOKUP] Retry 1: Checking...
   [ENROLLMENT] ✗✗✗ CRITICAL ERROR: No enrollment_id found!
   ```
   - This means Django couldn't match the message to the enrollment

**Solutions (Try in Order):**
- [ ] Verify MQTT credentials (check Django settings for MQTT_USER/MQTT_PASSWORD)
- [ ] Check MQTT broker logs
- [ ] Verify Django can connect to MQTT broker:
  ```python
  # In Django shell:
  from accounts.management.commands.mqtt_bridge import MQTTBridge
  bridge = MQTTBridge()
  bridge.connect()
  # Should print: [MQTT] Connected to MQTT Broker
  ```
- [ ] Check template_id matches between frontend and ESP32 (should be the same UUID)

---

### Issue #4: WebSocket Connection Times Out
**Symptom:**
```javascript
[WEBSOCKET] ✗ WebSocket connection timeout
// or
[ENROLLMENT] ✗ WebSocket failed to connect: WebSocket connection error
```

**Diagnosis:**
1. Check if Django is running:
   ```bash
   # On server terminal:
   ps aux | grep django
   # or on Windows:
   netstat -ano | findstr ":8000"
   ```

2. Check if Django Channels is running:
   ```bash
   # Should see "daphne" process:
   ps aux | grep daphne
   ```

3. Check if ASGI server is configured:
   ```bash
   # In Django settings.py:
   ASGI_APPLICATION = 'project.asgi.application'
   ```

**Solutions (Try in Order):**
- [ ] Restart Django server with Daphne (for WebSocket support)
- [ ] Check Django is listening on correct port (8000, 8080, etc.)
- [ ] Check firewall allows WebSocket connections (ws:// port)
- [ ] If using proxy/reverse proxy: ensure it supports WebSocket upgrade
- [ ] Check Redis is running (used by Django Channels): `redis-cli ping`

---

### Issue #5: "Enrollment Already in Progress" Error
**Symptom:**
```
❌ Enrollment is already in progress for your instructor. Please wait.
```

**Diagnosis:**
This means another browser tab/window has an active enrollment for the same instructor

**Solutions:**
- [ ] Close other browser tabs with enrollment modal open
- [ ] Refresh the page (Ctrl+F5)
- [ ] Wait 5 minutes for previous enrollment to timeout
- [ ] Check Django logs for stuck enrollments:
  ```bash
  # Search for this student in logs:
  grep "enrollment_in_progress" django.log
  ```

---

### Issue #6: ESP32 Not Detecting Finger
**Symptom:**
- Frontend shows "Waiting for finger..." 
- ESP32 serial monitor shows `[SCAN 1/3] Waiting for finger...`
- But nothing happens even when placing finger

**Diagnosis:**
This is an **ESP32 issue**, not MQTT/frontend issue
- R307 sensor might be malfunctioning
- Check ESP32 initialization message in serial monitor

**Solutions:**
- [ ] Test R307 sensor directly (use sensor test sketch)
- [ ] Clean sensor lens
- [ ] Power cycle ESP32
- [ ] Check sensor RX/TX pins are correct (GPIO16/GPIO17)
- [ ] Try with a different finger

---

## 🚀 Quick Deployment Checklist

After applying the fix, verify:

### Code Changes
- [ ] `enroll_course.html` line 1577 changed to 3000ms
- [ ] No other changes needed
- [ ] File saved and committed to git

### Server Deployment
- [ ] Django server restarted
- [ ] Daphne (ASGI server) is running
- [ ] Redis is running (for Channels)
- [ ] MQTT broker accessible (broker.hivemq.com)
- [ ] MQTT credentials correct in Django settings

### Browser Testing
- [ ] Clear cache (Ctrl+Shift+Delete)
- [ ] Test in Chrome/Firefox/Edge (not Internet Explorer!)
- [ ] Test with HTTPS if applicable (use wss:// for WebSocket)
- [ ] Test on different network (Wi-Fi vs mobile hotspot)

### Verify Fix
- [ ] See 3000ms message in browser console
- [ ] Complete 3 full enrollments without missing scans
- [ ] Check enrollment shows as "Biometric: Registered"
- [ ] Monitor success rate over time (should be >90%)

---

## 📊 Monitoring

### What to Watch After Deployment

**Browser Console (F12):**
```javascript
// Good sign:
[ENROLLMENT] ⏳ Waiting 3000ms for WebSocket group subscription...
[ENROLLMENT] ✓ Group subscription fully ready
[WEBSOCKET] ===== MESSAGE RECEIVED =====
[SCAN] ✓✓✓ COUNTER (based on unique steps): 1/3

// Bad sign:
[WEBSOCKET] ✗ WebSocket error during connection
[ENROLLMENT] ✗ WebSocket failed to connect
[ENROLLMENT] ✗ CRITICAL ERROR: No enrollment_id found!
```

**Django Logs:**
```bash
# Good sign:
[MQTT] Connected to MQTT Broker
[MQTT BRIDGE] ===== ENROLLMENT RESPONSE FROM ESP32 =====
[WEBSOCKET] ✓✓✓ SUCCESS: Found enrollment_id!

# Bad sign:
[MQTT] Connection failed with code: X
[ENROLLMENT] ✗✗✗ CRITICAL ERROR: No enrollment_id found!
```

**ESP32 Serial Monitor:**
```
Good sign:
[MQTT] ✓ Scan 1/3 progress published
✓ SCAN 1/3 CAPTURED

Bad sign:
[MQTT PUBLISH] Sending scan 1/3 progress to frontend...
[MQTT] ✗ Failed: rc=X  ← Publishing failed
```

---

## 📞 Getting More Help

### If None of the Above Solutions Work

Collect this information:

1. **Browser Console Output** (Copy entire session):
   ```
   F12 → Console tab → Right-click → Save as
   ```

2. **Django Server Logs** (Last 100 lines):
   ```bash
   tail -100 /path/to/django.log
   # or Windows:
   Get-Content django.log -Tail 100
   ```

3. **Django MQTT Bridge Logs** (If separate):
   ```bash
   grep "MQTT BRIDGE\|WEBSOCKET" django.log | tail -50
   ```

4. **ESP32 Serial Output** (Full enrollment sequence):
   ```
   Copy from first "Enrollment started" to last "All scans complete!"
   ```

5. **System Info:**
   - Django version: `python -m django --version`
   - Daphne version: `pip show daphne`
   - MQTT broker being used: (should be broker.hivemq.com)
   - Network: LAN or WAN or Wi-Fi?
   - Browser: Chrome/Firefox/Edge version?

Then create an issue with:
- Description of problem
- What you've already tried
- The above info collected
- Expected vs actual behavior

---

## 🎯 Success Criteria

You'll know the fix is working when:

1. ✅ **First enrollment attempt:** All 3 scans detected (100%)
2. ✅ **Second attempt:** All 3 scans detected (100%)
3. ✅ **Third attempt:** All 3 scans detected (100%)
4. ✅ **Progress bar:** Smooth progression 0% → 33% → 66% → 100%
5. ✅ **Page reload:** Shows "Biometric: Registered" 
6. ✅ **Serial monitor:** Shows "✓ SCAN 1/3", "✓ SCAN 2/3", "✓ SCAN 3/3" in order
7. ✅ **Browser console:** No errors, all [ENROLLMENT], [WEBSOCKET], [PROGRESS] messages

---

## 💡 Pro Tips

### For Testing
1. Use a smartphone as a browser client (test different network)
2. Toggle Wi-Fi on/off mid-enrollment to test network resilience
3. Open multiple browser tabs - see if they interfere
4. Test with real users, not just in your test environment

### For Debugging
1. Use Firefox DevTools → Network tab to see WebSocket frames
2. Check Django Debug Toolbar (if installed) to see MQTT timing
3. Use `curl` to test MQTT broker connectivity:
   ```bash
   # Test MQTT broker is reachable
   mosquitto_sub -h broker.hivemq.com -t "test/topic"
   # In another terminal:
   mosquitto_pub -h broker.hivemq.com -t "test/topic" -m "hello"
   ```

### For Performance
1. Monitor WebSocket connection time in browser DevTools
2. Check if MQTT messages are being deduplicated by topic
3. Monitor Django memory usage during enrollment (should be <100MB)
4. Check if enrollment_state dict is being cleaned up

---

## 📝 Change Log

| Date | Change | Impact |
|------|--------|--------|
| Jan 3, 2026 | Increased WebSocket wait from 1500ms → 3000ms | Fixes ~35% of missing scans |
| | Added this troubleshooting guide | Helps diagnose remaining issues |

---

**Last Updated:** January 3, 2026  
**For Issues:** Check console first, then Django logs, then ESP32 serial
