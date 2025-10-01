# D:\AISatyagrah\start_saty_web.ps1
param(
  [int]$Port = 8000,
  [string]$Host = "127.0.0.1",
  [switch]$Reload,
  [switch]$Kill,        # kill whatever is on $Port
  [switch]$PickNext,    # if occupied, auto-pick next free
  [switch]$NoBrowser,   # don’t open browser
  [switch]$NewWindow    # launch in separate console window
)

$ErrorActionPreference = 'Stop'
$root = 'D:\AISatyagrah'
$env:SATY_ROOT = $root

. "$root\scripts\ports.ps1"

# Choose final port
$finalPort = $Port
if (-not (Test-PortFree -Port $finalPort)) {
  if ($Kill) {
    $k = Stop-PortPids -Port $finalPort -Force
    if ($k.Count -gt 0) { Start-Sleep -Milliseconds 400 }
  } elseif ($PickNext) {
    $finalPort = Find-FreePort -StartPort $finalPort
  } else {
    Write-Error "Port $finalPort is in use. Re-run with -Kill or -PickNext."
  }
}

# Python path (venv first)
$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }

# Ensure deps (only if import fails)
try { & $py - <<<'import fastapi, uvicorn' 2>$null } catch { & $py -m pip install -U fastapi uvicorn }

# Build args
$reloadFlag = $Reload.IsPresent ? "--reload" : ""
$cmdArgs = @("$root\saty_web.py","--host",$Host,"--port",$finalPort,$reloadFlag) | Where-Object { $_ -ne "" }
$Url = "http://$Host`:$finalPort/"

Write-Host "Starting Web UI -> $Url" -ForegroundColor Cyan

if ($NewWindow) {
  # Detached console that stays open
  Start-Process -FilePath "$env:ComSpec" `
    -ArgumentList "/k `"$py`" `"$($cmdArgs -join '" "')`"" `
    -WorkingDirectory $root
} else {
  # Inline (blocks current shell)
  Push-Location $root
  & $py @cmdArgs
  Pop-Location
}

if (-not $NoBrowser) {
  Start-Process $Url | Out-Null
}
