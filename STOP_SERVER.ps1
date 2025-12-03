# ============================================
# STOP ALL SERVER PROCESSES
# ============================================
# This script forcefully stops all Python/Django processes

Write-Host ""
Write-Host "========================================" -ForegroundColor Red
Write-Host "  STOPPING ALL SERVER PROCESSES" -ForegroundColor Red
Write-Host "========================================" -ForegroundColor Red
Write-Host ""

# Step 1: Find all Python processes
Write-Host "[1/3] Finding Python processes..." -ForegroundColor Yellow
$pythonProcesses = Get-Process python -ErrorAction SilentlyContinue

if ($pythonProcesses) {
    Write-Host "    Found $($pythonProcesses.Count) Python process(es):" -ForegroundColor Yellow
    foreach ($proc in $pythonProcesses) {
        Write-Host "    - PID: $($proc.Id) | Name: $($proc.ProcessName) | Started: $($proc.StartTime)" -ForegroundColor White
    }
    
    # Step 2: Stop all Python processes
    Write-Host ""
    Write-Host "[2/3] Stopping all Python processes..." -ForegroundColor Yellow
    $pythonProcesses | Stop-Process -Force
    Start-Sleep -Seconds 2
    
    # Verify they're stopped
    $remaining = Get-Process python -ErrorAction SilentlyContinue
    if ($remaining) {
        Write-Host "    ⚠️  Some processes are still running. Force killing..." -ForegroundColor Red
        $remaining | Stop-Process -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 1
    }
    
    Write-Host "    ✅ All Python processes stopped" -ForegroundColor Green
} else {
    Write-Host "    ✅ No Python processes found" -ForegroundColor Green
}

# Step 3: Check if port 8000 is still in use
Write-Host ""
Write-Host "[3/3] Checking port 8000..." -ForegroundColor Yellow
$port8000 = netstat -ano | findstr :8000
if ($port8000) {
    Write-Host "    ⚠️  Port 8000 is still in use:" -ForegroundColor Yellow
    Write-Host "    $port8000" -ForegroundColor White
    Write-Host ""
    Write-Host "    To kill the process using port 8000, run:" -ForegroundColor Yellow
    Write-Host "    Get-NetTCPConnection -LocalPort 8000 | Select-Object -ExpandProperty OwningProcess | Stop-Process -Force" -ForegroundColor Cyan
} else {
    Write-Host "    ✅ Port 8000 is free" -ForegroundColor Green
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  SERVER STOPPED" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "All Python/Django processes have been stopped." -ForegroundColor White
Write-Host "You can now safely restart the server." -ForegroundColor White
Write-Host ""

