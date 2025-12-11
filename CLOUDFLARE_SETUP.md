# Cloudflare Tunnel Setup - Access Your Attendance System from Anywhere

## What is Cloudflare Tunnel?

Cloudflare Tunnel creates a **secure HTTPS public URL** for your local Django server. You can access your attendance system from your mobile phone or any device worldwide, with **camera access enabled**.

- ✅ **Free & Unlimited**
- ✅ **No deployment needed**
- ✅ **Camera/Microphone works**
- ✅ **Access from anywhere globally**
- ✅ **No port forwarding required**
- ✅ **Automatic HTTPS**

---

## Quick Start (3 Steps)

### **Step 1: Start Django Server**

```powershell
python manage.py runserver 0.0.0.0:8000
```

Keep this terminal open.

### **Step 2: Start Cloudflare Tunnel (New Terminal)**

**Option A - Using PowerShell Script (Recommended):**
```powershell
.\START_CLOUDFLARE_TUNNEL.ps1
```

**Option B - Using Batch File:**
```powershell
.\START_CLOUDFLARE_TUNNEL.bat
```

**Option C - Manual Command:**
```powershell
.\cloudflared.exe tunnel --url http://localhost:8000
```

### **Step 3: Access from Mobile**

The tunnel will output something like:
```
https://abc123-xyz789.trycloudflare.com
```

Copy this URL and open it in your mobile browser. **Camera will work automatically!**

---

## What You'll See

When you run the tunnel, you'll see:

```
2025-12-12T01:30:00Z INF Requesting new quick Tunnel token...
2025-12-12T01:30:02Z INF Obtained quick Tunnel token!

+----------------------------+---------------------+
|         ADDRESS             |      PROTOCOL       |
+----------------------------+---------------------+
| https://abc123-xyz789.trycloudflare.com | http  |
+----------------------------+---------------------+

Your quick Tunnel has been created! Visiting it: https://abc123-xyz789.trycloudflare.com
```

**That URL is your public address!** Share it with anyone to access your system.

---

## Features

### **Camera Access**
- ✅ Works on HTTPS (automatic with Cloudflare)
- ✅ Permissions already configured
- ✅ Mobile phones can access camera

### **Security**
- ✅ HTTPS encryption
- ✅ Cloudflare DDoS protection
- ✅ No port forwarding needed
- ✅ Isolated tunnel session

### **Performance**
- ✅ Fast global CDN
- ✅ Low latency
- ✅ Unlimited bandwidth

---

## Troubleshooting

### **"Django server not running"**
Make sure you run this first in a separate terminal:
```powershell
python manage.py runserver 0.0.0.0:8000
```

### **"Connection refused"**
- Check if Django is running on port 8000
- Verify no firewall is blocking it

### **"Camera still not working"**
- Make sure you're using **HTTPS** (Cloudflare provides this)
- Allow camera permissions in browser settings
- Try a different browser (Chrome/Firefox works best)

### **"Tunnel stopped"**
The URL changes each time you restart. This is normal for free tier.

---

## Advanced: Keep URL Permanent (Optional)

For a permanent URL, you need to authenticate with Cloudflare:

```powershell
.\cloudflared.exe login
```

This opens your browser to authenticate. Then:

```powershell
.\cloudflared.exe tunnel create attendance
.\cloudflared.exe tunnel route dns attendance attendance.yourdomain.com
```

But for testing, the quick tunnel is perfect!

---

## Files Included

- `cloudflared.exe` - Cloudflare Tunnel executable
- `START_CLOUDFLARE_TUNNEL.ps1` - PowerShell starter script
- `START_CLOUDFLARE_TUNNEL.bat` - Batch starter script
- `CLOUDFLARE_SETUP.md` - This guide

---

## Access Pattern

```
Your Computer         Cloudflare Tunnel      Mobile Phone
    |                      |                      |
    | localhost:8000 <---> | HTTPS Public URL <-- |
    | Django Server        | abc123.trycloudflare.com
    |________________      |_______________________
```

---

## Next Steps

1. ✅ Start Django: `python manage.py runserver 0.0.0.0:8000`
2. ✅ Start Tunnel: `.\START_CLOUDFLARE_TUNNEL.ps1`
3. ✅ Copy public URL
4. ✅ Access from mobile
5. ✅ Test camera access

---

## Support

If you need help:
- Check Django is running: `http://localhost:8000` (should work locally)
- Test tunnel is working: Copy the URL from tunnel output
- Camera not working: Try in Chrome/Firefox, allow permissions

Enjoy your global attendance system! 🎉
