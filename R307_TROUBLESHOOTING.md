# R307 Fingerprint Sensor Troubleshooting Guide

## Problem Summary
The sensor is **detected** at startup (verifyPassword() works) but **finger placement shows no detection** (getImage() always returns NOFINGER).

## Critical Checks

### 1. **WIRING - VERIFY CONNECTIONS**
Current code expects:
- **RX (input from sensor)**: GPIO16
- **TX (output to sensor)**: GPIO17
- **VCC**: 5V power
- **GND**: Ground

**CHECK**:
```
R307 Pin  →  ESP32 Pin
TX        →  GPIO16 (RX on ESP32)
RX        →  GPIO17 (TX on ESP32)
5V        →  5V
GND       →  GND
```

⚠️ **IF WIRES ARE SWAPPED**: Sensor verification works but getImage() fails!

### 2. **POWER SUPPLY**
- Check **5V power supply** is stable (not 3.3V)
- R307 requires **reliable 5V power**
- Low power causes intermittent failures
- Check LED on R307: should be **glowing steady**

### 3. **SENSOR LED**
- Green LED should be **ON** (steady or blinking)
- If OFF: no power or bad connection
- If flickering rapidly: communication issue

### 4. **SERIAL BAUD RATE**
- Current: **57600 baud**
- R307 default is usually 57600
- Can be: 9600, 19200, 38400, 57600, 115200
- If unsure, try testing at different baud rates

### 5. **CLEAN THE SENSOR**
- Use soft, **dry, lint-free cloth**
- Do NOT use water or alcohol
- Dust/dirt blocks optical sensor
- Test with different fingers

## Test Procedure

1. **Open Serial Monitor**:
   ```bash
   cd "path to project"
   pio device monitor --baud 115200
   ```

2. **Visit test endpoint**:
   - Open browser: `http://192.168.1.10/test`
   - Firmware will run 30-second detection test
   - **PLACE FINGER ON SENSOR IMMEDIATELY**
   - Keep finger still for entire duration

3. **Watch Serial Output**:
   ```
   [3s] NOFINGER=X, OK=Y, Errors=Z - Waiting...
   ```
   - If `OK` stays at 0: sensor not detecting finger
   - If `NOFINGER` high: sensor sees empty surface
   - If `Errors` high: communication problem

## Expected vs Actual

### ✓ WORKING (detection happens):
```
[0s] NOFINGER=0, OK=1, Errors=0 - Waiting...
✓✓✓ FINGER DETECTED! ✓✓✓
Your sensor is working correctly!
```

### ✗ NOT WORKING (no detection):
```
[3s] NOFINGER=30, OK=0, Errors=0
[6s] NOFINGER=60, OK=0, Errors=0
...
✗ NO FINGER DETECTED
```

## Solutions to Try (in order)

### Solution 1: Check Wiring
- Verify RX/TX not swapped (see Wiring section)
- Check all connections are firm
- No loose connections

### Solution 2: Try Different Baud Rate
Edit [src/main.cpp](src/main.cpp) line ~76, change:
```cpp
fingerSerial.begin(57600, SERIAL_8N1, 16, 17);
```

Try values:
- `115200` 
- `38400`
- `19200`
- `9600`

### Solution 3: Clean Sensor
- Gently wipe sensor with dry cloth
- Remove any dust or fingerprints
- Let dry completely

### Solution 4: Power Supply Check
- Use separate 5V power supply (not USB)
- If using USB: add capacitor (100µF) to R307 VCC
- Test with different power source

### Solution 5: Different GPIO Pins
If above fails, try alternative pins:
- Change `16` and `17` in line ~76 to `4` and `5`
- Or `32` and `33` (these are usually available)

### Solution 6: Factory Reset
Some R307 sensors have bad calibration. Try:
1. Power off sensor
2. Wait 10 seconds
3. Power on
4. Reflash firmware

## Hardware Alternatives

If sensor still doesn't work, it might be:
- **R307 defective** - try replacement
- **Different version** - R307 V3.0 vs older versions differ
- **Wrong pinout** - verify your specific module's pinout

## Contact & Debugging

If all above fails:
1. Verify sensor model: Check label on R307
2. Test with different Arduino/ESP32 board
3. Create serial analyzer trace (advanced)
4. Consider sensor replacement

---

**Last Updated**: December 25, 2025
**Firmware Version**: Latest with enhanced diagnostics
