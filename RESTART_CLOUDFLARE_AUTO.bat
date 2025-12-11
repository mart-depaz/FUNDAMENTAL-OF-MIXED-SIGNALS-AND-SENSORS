@echo off
REM Auto-restart Cloudflare Tunnel - keeps tunnel alive

setlocal enabledelayedexpansion

cd /d "%~dp0"

echo.
echo ========================================
echo Cloudflare Tunnel - Auto Restart
echo ========================================
echo.
echo This will automatically restart the tunnel if it crashes
echo.

:loop
echo [%date% %time%] Starting Cloudflare Tunnel...
.\cloudflared.exe tunnel --url http://localhost:8000

echo.
echo [%date% %time%] Tunnel disconnected! Restarting in 5 seconds...
timeout /t 5 /nobreak

goto loop
