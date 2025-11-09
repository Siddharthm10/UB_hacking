$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

# Ensure backend env
if (-not (Test-Path "$root\backend\.env")) {
  Copy-Item "$root\backend\.env.example" "$root\backend\.env" -Force
}

# Paths
$py = "$root\backend\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) { Write-Host "Python venv not found at $py" -ForegroundColor Yellow }

# Start backend (new window)
Start-Process powershell -ArgumentList "-NoLogo -NoProfile -Command cd '$root'; & '$py' -m backend.app" -WindowStyle Minimized

# Start frontend (new window)
Start-Process powershell -ArgumentList "-NoLogo -NoProfile -Command cd '$root\my-dashboard'; npm install --no-fund; npm run dev" -WindowStyle Minimized

Write-Host "EthiCo Live starting..." -ForegroundColor Green
Write-Host "Open http://localhost:5173" -ForegroundColor Cyan

