# Start SYNiq on this lab computer (Windows 10 or 11 with Docker Desktop) and show the address students type.
# Safe to run again at any time. Double-click start-windows.bat, or run:  powershell -ExecutionPolicy Bypass -File start.ps1
param([switch]$Update)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Say($text) { Write-Host ""; Write-Host "== $text" -ForegroundColor Yellow }
function Stop-With($text) { Write-Host $text -ForegroundColor Red; Read-Host "Press Enter to close"; exit 1 }

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { Stop-With "Docker Desktop is not installed. See docs/lab-pilot.md, step 2." }
docker info *> $null
if ($LASTEXITCODE -ne 0) { Stop-With "Docker Desktop is not running. Open Docker Desktop, wait until it says 'Engine running', then try again." }

if ($Update) {
  Say "Getting the newest SYNiq"
  git -C ..\.. pull --ff-only
}

$utf8 = New-Object System.Text.UTF8Encoding($false)
if (-not (Test-Path .env)) {
  Say "First start: making a database password"
  $bytes = New-Object byte[] 24
  [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
  $password = ([Convert]::ToBase64String($bytes)) -replace '[/+=]', ''
  $lines = Get-Content .env.example | ForEach-Object { if ($_ -like 'POSTGRES_PASSWORD=*') { "POSTGRES_PASSWORD=$password" } else { $_ } }
  [IO.File]::WriteAllLines((Join-Path $PSScriptRoot ".env"), $lines, $utf8)
  Write-Host "Saved in deploy\lab\.env. Keep a copy of that file somewhere safe (not on this computer only)."
}
$port = ((Get-Content .env | Where-Object { $_ -like 'PORT=*' }) -replace 'PORT=', '').Trim()
if (-not $port) { $port = "80" }

Say "Starting SYNiq (the first time takes 5 to 15 minutes and needs internet)"
docker compose up -d --build
if ($LASTEXITCODE -ne 0) { Stop-With "Docker could not start SYNiq. See the messages above." }

Say "Waiting for SYNiq to answer"
$ready = $false
for ($i = 0; $i -lt 90; $i++) {
  try { Invoke-WebRequest -UseBasicParsing "http://localhost:$port/api/health" -TimeoutSec 3 | Out-Null; $ready = $true; break } catch { Start-Sleep 2 }
}
if (-not $ready) { Stop-With "SYNiq did not answer after 3 minutes. See what went wrong with: docker compose logs --tail 50 api" }

if (-not (Test-Path .admin-created)) {
  Say "Create the school admin (the person who adds students and teachers)"
  $email = Read-Host "Admin email"
  while ($true) {
    $p1 = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR((Read-Host "Admin password (at least 8 characters)" -AsSecureString)))
    $p2 = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR((Read-Host "Type it again" -AsSecureString)))
    if ($p1 -eq $p2 -and $p1.Length -ge 8) { break }
    Write-Host "The two did not match or were too short. Try again."
  }
  docker compose exec -T -e "SYNIQ_ADMIN_EMAIL=$email" -e "SYNIQ_ADMIN_PASSWORD=$p1" api python -m app.bootstrap
  if ($LASTEXITCODE -eq 0) { New-Item .admin-created -ItemType File | Out-Null }
}

Say "SYNiq is running"
$suffix = if ($port -ne "80") { ":$port" } else { "" }
$addresses = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
  Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' -and $_.InterfaceAlias -notlike '*vEthernet*' -and $_.InterfaceAlias -notlike '*WSL*' }
if ($addresses) {
  Write-Host "On the school Wi-Fi, students and teachers open:"
  foreach ($a in $addresses) { Write-Host "    http://$($a.IPAddress)$suffix" -ForegroundColor Green }
} else {
  Write-Host "Could not find this computer's network address. Check it is connected to the school network."
}
Write-Host "On this computer itself:  http://localhost$suffix"
Write-Host "Backups are saved every day in deploy\lab\backups. Copy that folder to a pen drive every week."
Read-Host "Press Enter to close (SYNiq keeps running)"
