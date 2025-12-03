# 🛑 How to Stop the Django Server

## The Problem

Sometimes when you press `Ctrl + C` to stop the server, it doesn't fully stop. This happens because:
1. The process might be running in the background
2. Multiple Python processes might be running
3. The port (8000) might still be in use
4. The terminal window might have closed but the process continues

## ✅ Solutions

### Method 1: Use the Stop Script (Recommended)

Run this PowerShell script from the `library_system` folder:

```powershell
.\STOP_SERVER.ps1
```

This will:
- ✅ Find all Python processes
- ✅ Stop them forcefully
- ✅ Check if port 8000 is free
- ✅ Show you what's running

### Method 2: Manual Stop (PowerShell)

```powershell
# Stop all Python processes
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force

# Clear port 8000
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | 
    Select-Object -ExpandProperty OwningProcess | 
    Stop-Process -Force
```

### Method 3: Using Task Manager

1. Press `Ctrl + Shift + Esc` to open Task Manager
2. Go to "Details" tab
3. Look for `python.exe` processes
4. Right-click → "End task"

### Method 4: Using Command Prompt

```cmd
# Find Python processes
tasklist | findstr python

# Kill by PID (replace XXXX with the actual PID)
taskkill /PID XXXX /F

# Or kill all Python processes
taskkill /IM python.exe /F
```

## 🔍 Check if Server is Still Running

### Check Python Processes
```powershell
Get-Process python -ErrorAction SilentlyContinue
```

If this shows nothing, no Python processes are running.

### Check Port 8000
```powershell
netstat -ano | findstr :8000
```

If this shows nothing, port 8000 is free.

### Try Accessing the Server
Open your browser and go to: `http://127.0.0.1:8000`

- If it loads → Server is still running
- If it doesn't load → Server is stopped

## ⚠️ Why This Happens

1. **Background Processes**: Django might spawn child processes
2. **Multiple Terminals**: Server might be running in another terminal window
3. **IDE Integration**: Some IDEs keep processes running
4. **Process Hanging**: Sometimes `Ctrl + C` doesn't work if the process is stuck

## 💡 Prevention Tips

1. **Always use the stop script** before restarting:
   ```powershell
   .\STOP_SERVER.ps1
   ```

2. **Check before starting**:
   ```powershell
   # Check if anything is running
   Get-Process python -ErrorAction SilentlyContinue
   ```

3. **Use one terminal** for the server to avoid confusion

4. **Close terminal properly** - Don't just close the window, stop the process first

## 🚨 If Nothing Works

If the server still won't stop:

1. **Restart your computer** - This will kill all processes

2. **Change the port** in `manage.py runserver`:
   ```powershell
   python manage.py runserver 8001
   ```

3. **Use a different port** in the cache fix script:
   Edit `COMPLETE_CACHE_FIX.ps1` and change `8000` to `8001`

## 📝 Quick Reference

| Command | What it does |
|---------|-------------|
| `.\STOP_SERVER.ps1` | Stops all Python processes |
| `Get-Process python` | Shows running Python processes |
| `netstat -ano \| findstr :8000` | Shows what's using port 8000 |
| `taskkill /IM python.exe /F` | Force kill all Python (CMD) |

---

**Remember**: Always stop the server properly before restarting to avoid port conflicts!

