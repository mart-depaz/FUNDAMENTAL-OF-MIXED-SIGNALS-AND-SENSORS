@echo off
REM Start Cloudflare Tunnel - Access your Django app from anywhere with camera support

echo.
echo ========================================
echo Cloudflare Tunnel - Attendance System
echo ========================================
echo.
echo Starting tunnel to http://localhost:8000
echo.
echo Your app will be available at a public HTTPS URL
echo Camera access will work automatically
echo.
echo Press Ctrl+C to stop
echo.

cd /d "%~dp0"
.\cloudflared.exe tunnel --url http://localhost:8000
pause
