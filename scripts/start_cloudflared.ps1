<#
Usage:
  - Open PowerShell and run: `.	ools\start_cloudflared.ps1`
  - This will open a new terminal for Django and a new terminal for Cloudflared.
Prerequisites:
  - Python in PATH (or use full path to python)
  - `cloudflared.exe` available in repository root or installed in PATH
#>

$Repo = Split-Path -Parent $MyInvocation.MyCommand.Definition
if (-not $Repo) { $Repo = Get-Location }
Write-Host "Repository: $Repo"

# Stop any existing cloudflared/python instances started by previous runs (best-effort)
Get-Process cloudflared -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
# Note: we do not forcibly kill all python processes to avoid collateral stops

# Start Django in a new PowerShell window
$djangoCmd = "cd `"$Repo`"; python manage.py runserver 0.0.0.0:8000 --nothreading --noreload"
Write-Host "Starting Django: $djangoCmd"
Start-Process powershell -ArgumentList "-NoExit","-Command","$djangoCmd"

Start-Sleep -Seconds 2

# Start cloudflared in a new PowerShell window so you can see the generated URL
$cloudflaredExe = Join-Path $Repo 'cloudflared.exe'
if (Test-Path $cloudflaredExe) {
    $cloudCmd = ".\cloudflared.exe tunnel --url http://localhost:8000"
} else {
    $cloudCmd = "cloudflared tunnel --url http://localhost:8000"
}
Write-Host "Starting Cloudflared: $cloudCmd"
Start-Process powershell -ArgumentList "-NoExit","-Command","cd `"$Repo`"; $cloudCmd"

Write-Host "Started Django and Cloudflared. Check the Cloudflared terminal for the public URL (trycloudflare.com)."