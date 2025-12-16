# D:\AISatyagrah\scripts\run_server.ps1
param(
  [string]$Token = "",
  [string]$Bind = "127.0.0.1",
  [int]$Port = 9000,
  [switch]$Reload
)

$ErrorActionPreference = "Stop"

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$py   = Join-Path $root ".venv\Scripts\python.exe"

if (!(Test-Path $py)) {
  throw "Missing venv python: $py  (create venv at $root\.venv)"
}

if ($Token -ne "") {
  $env:AUTH_TOKEN = $Token
  Write-Host "AUTH_TOKEN set (auth ON)" -ForegroundColor Green
} else {
  Remove-Item Env:\AUTH_TOKEN -ErrorAction SilentlyContinue
  Write-Host "AUTH_TOKEN not set (auth OFF)" -ForegroundColor Yellow
}

$reloadArgs = @()
if ($Reload) { $reloadArgs = @("--reload") }

Write-Host "Starting: http://$Bind`:$Port" -ForegroundColor Cyan
Write-Host "Module: satyagrah.web.jobs_api:app" -ForegroundColor Cyan

& $py -m uvicorn satyagrah.web.jobs_api:app --host $Bind --port $Port @reloadArgs

