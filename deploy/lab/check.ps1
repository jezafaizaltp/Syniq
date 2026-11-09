# Check the Windows lab computer is ready before a class: SYNiq running, reachable on the school network,
# enough free disk space, and a recent backup. Changes nothing. Run it 10 minutes before the lab period.
# Double-click check-windows.bat, or run:  powershell -ExecutionPolicy Bypass -File check.ps1
Set-Location $PSScriptRoot

$script:problems = 0
$script:warnings = 0
function Ok($text)   { Write-Host "  OK     $text" -ForegroundColor Green }
function Warn($text) { Write-Host "  CHECK  $text" -ForegroundColor Yellow; $script:warnings++ }
function Fail($text) { Write-Host "  FIX    $text" -ForegroundColor Red; $script:problems++ }
function Answers($url) {
  try { Invoke-WebRequest -UseBasicParsing $url -TimeoutSec 5 | Out-Null; return $true } catch { return $false }
}
function Finish($code) { Write-Host ""; Read-Host "Press Enter to close" | Out-Null; exit $code }

$port = "80"
if (Test-Path .env) {
  $line = Get-Content .env | Where-Object { $_ -like 'PORT=*' } | Select-Object -First 1
  if ($line) { $port = ($line -replace 'PORT=', '').Trim() }
}
if (-not $port) { $port = "80" }
$suffix = if ($port -ne "80") { ":$port" } else { "" }

Write-Host ("SYNiq lab check, " + (Get-Date -Format "dd MMM yyyy HH:mm"))

# 1. Docker Desktop and the five parts of SYNiq
$dockerOk = $false
if (Get-Command docker -ErrorAction SilentlyContinue) {
  docker info *> $null
  $dockerOk = ($LASTEXITCODE -eq 0)
}
if (-not $dockerOk) {
  Fail "Docker Desktop is not running. Open it, wait for 'Engine running', then double-click start-windows.bat"
} else {
  $running = @(docker compose ps --status running --services 2>$null)
  $missing = @("api", "backup", "caddy", "db", "web" | Where-Object { $running -notcontains $_ })
  if ($missing.Count -eq 0) { Ok "All five parts of SYNiq are running" }
  else { Fail ("Not running: " + ($missing -join ", ") + ". Double-click start-windows.bat, or see: docker compose logs --tail 50 " + ($missing -join " ")) }
}

# 2. SYNiq answers on this computer
if (Answers "http://localhost$suffix/api/health") { Ok "SYNiq answers at http://localhost$suffix" }
else { Fail "SYNiq does not answer at http://localhost$suffix. Double-click start-windows.bat" }

# 3. The network address students type
$addresses = @(Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
  Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' -and $_.InterfaceAlias -notlike '*vEthernet*' -and $_.InterfaceAlias -notlike '*WSL*' } |
  ForEach-Object { $_.IPAddress })
if ($addresses.Count -eq 0) {
  Fail "No school network address found. Connect this computer to the school Wi-Fi or cable."
} else {
  foreach ($a in $addresses) {
    if (Answers "http://$a$suffix/api/health") { Ok "Students open http://$a$suffix" }
    else { Fail "SYNiq does not answer at http://$a$suffix. Double-click start-windows.bat" }
  }
  $now = ($addresses | Sort-Object) -join " "
  if (Test-Path .last-address) {
    $before = (Get-Content .last-address -Raw).Trim()
    if ($before -and $before -ne $now) {
      Warn "The address changed since the last check (was $before). Login slips and bookmarks show the old one: see docs/lab-pilot.md step 5."
    }
  }
  Set-Content -Path .last-address -Value $now -NoNewline
}
# Windows Firewall: a network marked Public blocks other computers by default.
$public = @(Get-NetConnectionProfile -ErrorAction SilentlyContinue | Where-Object { $_.NetworkCategory -eq 'Public' })
if ($public.Count -gt 0) {
  Warn ("Windows calls the network '" + $public[0].Name + "' Public, which can block students. Set it to Private in Settings > Network & internet.")
}

# 4. Free disk space
$drive = (Get-Item $PSScriptRoot).PSDrive
$freeGb = [math]::Floor($drive.Free / 1GB)
if ($freeGb -lt 2) { Fail "Only $freeGb GB free on drive $($drive.Name):. Delete old files, or SYNiq may stop saving work." }
elseif ($freeGb -lt 5) { Warn "$freeGb GB free on drive $($drive.Name):. Make room soon (5 GB or more is comfortable)." }
else { Ok "$freeGb GB free on drive $($drive.Name):" }

# 5. A recent backup
$backups = @(Get-ChildItem -Path backups -Filter 'syniq-*.sql.gz' -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending)
if ($backups.Count -eq 0) {
  Fail "No backup found in deploy\lab\backups. Make one now: docker compose restart backup"
} else {
  $newest = $backups[0]
  $ageH = [math]::Floor(((Get-Date) - $newest.LastWriteTime).TotalHours)
  $looksOk = $false
  try {
    $stream = [IO.File]::OpenRead($newest.FullName)
    $gzip = New-Object IO.Compression.GZipStream($stream, [IO.Compression.CompressionMode]::Decompress)
    $reader = New-Object IO.StreamReader($gzip)
    $buffer = New-Object char[] 100000
    $n = $reader.Read($buffer, 0, $buffer.Length)
    $looksOk = ([string]::new($buffer, 0, $n)).Contains("CREATE TABLE")
    $reader.Close()
  } catch { $looksOk = $false }
  if (-not $looksOk) { Fail "The newest backup ($($newest.Name)) looks broken. Make one now: docker compose restart backup" }
  elseif ($ageH -gt 30) { Fail "The newest backup is $ageH hours old. Make one now: docker compose restart backup" }
  else { Ok "Newest backup $($newest.Name) is $ageH hours old" }
  if (((Get-Date) - $backups[-1].LastWriteTime).TotalDays -ge 7) {
    Write-Host "  NOTE   Copy deploy\lab\backups to the pen drive once a week."
  }
}

Write-Host ""
if ($script:problems -gt 0) {
  Write-Host "$($script:problems) thing(s) to fix before students start." -ForegroundColor Red
  Finish 1
}
if ($script:warnings -gt 0) { Write-Host "Ready, with $($script:warnings) thing(s) to check." -ForegroundColor Yellow }
else { Write-Host "Ready for the class." -ForegroundColor Green }
Finish 0
