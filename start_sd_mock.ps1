# D:\AISatyagrah\start_sd_mock.ps1
param(
  [int]$Port = 7860,
  [string]$Host = "127.0.0.1",
  [switch]$Kill,
  [switch]$PickNext,
  [switch]$NewWindow
)

$ErrorActionPreference = 'Stop'
$root = 'D:\AISatyagrah'
$env:SATY_ROOT = $root

. "$root\scripts\ports.ps1"

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

$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }

# Ensure deps
try { & $py - <<<'import fastapi, uvicorn' 2>$null } catch { & $py -m pip install -U fastapi uvicorn }

$cmd = @("-m","uvicorn","satyagrah.mock_sdapi:app","--host",$Host,"--port",$finalPort)
$Url = "http://$Host`:$finalPort/"

Write-Host "Starting SD mock -> $Url" -ForegroundColor Cyan

if ($NewWindow) {
  Start-Process -FilePath "$env:ComSpec" `
    -ArgumentList "/k `"$py`" $($cmd -join ' ')" `
    -WorkingDirectory $root
} else {
  Push-Location $root
  & $py @cmd
  Pop-Location
}
