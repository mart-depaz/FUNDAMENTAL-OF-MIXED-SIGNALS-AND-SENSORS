# Cloudflare Tunnel Starter Script for Attendance System
# This script starts a public HTTPS tunnel to your local Django server

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Cloudflare Tunnel - Attendance System" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if Django server is running
Write-Host "Checking if Django server is running on port 8000..." -ForegroundColor Yellow

$testConnection = $null
try {
    $testConnection = Test-NetConnection -ComputerName localhost -Port 8000 -WarningAction SilentlyContinue
} catch {
    $testConnection = $null
}

if ($testConnection -and $testConnection.TcpTestSucceeded) {
    Write-Host "✓ Django server is running!" -ForegroundColor Green
} else {
    Write-Host "✗ Django server is NOT running on port 8000" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please start Django first:" -ForegroundColor Yellow
    Write-Host "  python manage.py runserver 0.0.0.0:8000" -ForegroundColor White
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit
}

Write-Host ""
Write-Host "Starting Cloudflare Tunnel..." -ForegroundColor Cyan
Write-Host "This will create a public HTTPS URL for your attendance system" -ForegroundColor Gray
Write-Host ""

# Run cloudflared tunnel
& .\cloudflared.exe tunnel --url http://localhost:8000

Read-Host "Press Enter to exit"
