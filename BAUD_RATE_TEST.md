# R307 Baud Rate Test Instructions

The R307 fingerprint sensor may be configured at a different baud rate than 57600.

## Quick Test

1. **Open a terminal** in your project folder
2. **Try each baud rate** (run one at a time):

```powershell
# Connect at different baud rates
pio device monitor --baud 9600
pio device monitor --baud 19200
pio device monitor --baud 38400
pio device monitor --baud 57600    # Current setting
pio device monitor --baud 115200
```

3. With each monitor open, **place your finger on the sensor**
4. If you see output appearing correctly, that's likely the right baud rate

## Change Firmware Baud Rate

Once you identify the correct baud rate:

1. Open `src/main.cpp`
2. Find line ~76:
   ```cpp
   fingerSerial.begin(57600, SERIAL_8N1, 16, 17);
   ```
   and also
   ```cpp
   finger.begin(57600);
   ```

3. Replace `57600` with your detected baud rate
4. Save and upload:
   ```bash
   pio run -t upload -e esp32doit-devkit-v1
   ```

## Common Baud Rates

- **9600**: Older R307 versions
- **19200**: Some variants
- **38400**: Uncommon but possible
- **57600**: Default/most common
- **115200**: Newer versions or reconfigured sensors

---

If the sensor works at a different baud rate than 57600, let me know and I'll update the firmware!
