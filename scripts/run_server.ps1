param(
  [int]$Port = 9000,
  [string]$Host = "127.0.0.1",
  [string]$Token = $env:AUTH_TOKEN,
  [switch]$NoAuth
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path "$PSScriptRoot\..").Path
Set-Location $root

if ($NoAuth) {
  Remove-Item Env:\AUTH_TOKEN -ErrorAction SilentlyContinue
  Write-Host "AUTH_TOKEN cleared (auth OFF)" -ForegroundColor Yellow
} elseif ($Token) {
  $env:AUTH_TOKEN = $Token
  Write-Host "AUTH_TOKEN set (auth ON)" -ForegroundColor Green
} else {
  Write-Host "AUTH_TOKEN not set (auth OFF)" -ForegroundColor Yellow
}

Write-Host "Starting: uvicorn satyagrah.web.jobs_api:app on http://$Host`:$Port" -ForegroundColor Cyan
uvicorn satyagrah.web.jobs_api:app --host $Host --port $Port --reload
