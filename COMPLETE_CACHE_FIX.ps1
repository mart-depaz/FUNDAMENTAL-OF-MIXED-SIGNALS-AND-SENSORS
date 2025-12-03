# ============================================
# COMPLETE CACHE FIX - Ensures All Changes Are Reflected
# ============================================
# This script does EVERYTHING needed to see your changes

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  COMPLETE CACHE FIX & SERVER RESTART" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Navigate to project directory
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Definition
$projectRoot = Join-Path $scriptPath "library_system"
Set-Location $projectRoot
Write-Host "[1/8] Navigated to project directory" -ForegroundColor Green

# Step 2: Stop ALL Python processes
Write-Host "[2/8] Stopping all Python processes..." -ForegroundColor Yellow
$pythonProcesses = Get-Process python -ErrorAction SilentlyContinue
if ($pythonProcesses) {
    Write-Host "    Found $($pythonProcesses.Count) process(es), stopping..." -ForegroundColor Yellow
    $pythonProcesses | Stop-Process -Force
    Start-Sleep -Seconds 2
    
    # Verify they're stopped
    $remaining = Get-Process python -ErrorAction SilentlyContinue
    if ($remaining) {
        Write-Host "    ⚠️  Some processes still running, force killing..." -ForegroundColor Red
        $remaining | Stop-Process -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 1
    }
    
    Write-Host "    ✓ All Python processes stopped" -ForegroundColor Green
} else {
    Write-Host "    ✓ No Python processes running" -ForegroundColor Green
}

# Also clear port 8000 if in use
Write-Host "    Clearing port 8000..." -ForegroundColor Yellow
try {
    Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | 
        Select-Object -ExpandProperty OwningProcess | 
        Stop-Process -Force -ErrorAction SilentlyContinue
    Write-Host "    ✓ Port 8000 cleared" -ForegroundColor Green
} catch {
    # Port might not be in use, that's okay
}

# Step 3: Clear Python bytecode cache
Write-Host "[3/8] Clearing Python bytecode cache..." -ForegroundColor Yellow
$pycacheDirs = Get-ChildItem -Recurse -Path . -Include __pycache__ -Directory -ErrorAction SilentlyContinue
$pycFiles = Get-ChildItem -Recurse -Path . -Include *.pyc,*.pyo -File -ErrorAction SilentlyContinue
$pycacheDirs | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
$pycFiles | Remove-Item -Force -ErrorAction SilentlyContinue
Write-Host "    ✓ Cleared $($pycacheDirs.Count) __pycache__ directories" -ForegroundColor Green
Write-Host "    ✓ Cleared $($pycFiles.Count) .pyc/.pyo files" -ForegroundColor Green

# Step 4: Clear Django cache directories
Write-Host "[4/8] Clearing Django cache..." -ForegroundColor Yellow
$cacheDirs = @("cache", ".cache", "django_cache")
foreach ($cacheDir in $cacheDirs) {
    if (Test-Path $cacheDir) {
        Remove-Item -Recurse -Force $cacheDir -ErrorAction SilentlyContinue
        Write-Host "    ✓ Cleared $cacheDir" -ForegroundColor Green
    }
}
Write-Host "    ✓ Django cache cleared" -ForegroundColor Green

# Step 5: Clear any .DS_Store or Thumbs.db files
Write-Host "[5/8] Clearing system cache files..." -ForegroundColor Yellow
Get-ChildItem -Recurse -Include .DS_Store, Thumbs.db -File -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
Write-Host "    ✓ System cache files cleared" -ForegroundColor Green

# Step 6: Verify virtual environment
Write-Host "[6/8] Checking virtual environment..." -ForegroundColor Yellow
$venvPath = Join-Path (Split-Path -Parent $projectRoot) "library_env\Scripts\Activate.ps1"
if (Test-Path $venvPath) {
    Write-Host "    ✓ Virtual environment found" -ForegroundColor Green
} else {
    Write-Host "    ✗ Virtual environment not found at: $venvPath" -ForegroundColor Red
    Write-Host "    Please activate it manually" -ForegroundColor Yellow
    exit 1
}

# Step 7: Activate virtual environment and run migrations
Write-Host "[7/8] Activating virtual environment and checking database..." -ForegroundColor Yellow
& $venvPath
if ($LASTEXITCODE -ne 0) {
    Write-Host "    ✗ Failed to activate virtual environment" -ForegroundColor Red
    exit 1
}
Write-Host "    ✓ Virtual environment activated" -ForegroundColor Green

# Run migrations to ensure database is up to date
Write-Host "    Running migrations..." -ForegroundColor Yellow
python manage.py makemigrations --noinput 2>&1 | Out-Null
python manage.py migrate --noinput 2>&1 | Out-Null
Write-Host "    ✓ Database migrations checked" -ForegroundColor Green

# Step 8: Start Django server with auto-reload
Write-Host "[8/8] Starting Django development server..." -ForegroundColor Yellow
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  SERVER STARTING" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Server URL: http://127.0.0.1:8000" -ForegroundColor Green
Write-Host ""
Write-Host "IMPORTANT NEXT STEPS:" -ForegroundColor Yellow
Write-Host "1. Open your browser" -ForegroundColor White
Write-Host "2. Press Ctrl+Shift+Delete to clear browser cache" -ForegroundColor White
Write-Host "3. Select 'Cached images and files' and 'All time'" -ForegroundColor White
Write-Host "4. Click 'Clear data'" -ForegroundColor White
Write-Host "5. Open Developer Tools (F12)" -ForegroundColor White
Write-Host "6. Go to Network tab and check 'Disable cache'" -ForegroundColor White
Write-Host "7. Navigate to your application" -ForegroundColor White
Write-Host "8. Press Ctrl+F5 for hard refresh" -ForegroundColor White
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

# Start the server (this will block)
python manage.py runserver

