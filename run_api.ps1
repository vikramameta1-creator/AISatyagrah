param(
  [string]$Host = "127.0.0.1",
  [int]$Port = 9000
)
$ErrorActionPreference = "Stop"
if (-not $env:AUTH_TOKEN) { $env:AUTH_TOKEN = "mysupersecrettoken" }
if (-not $env:REDIS_URL)  { $env:REDIS_URL  = "redis://127.0.0.1:6379/0" }

New-Item -ItemType Directory -Force -Path "$PSScriptRoot\logs" | Out-Null
$log = Join-Path $PSScriptRoot "logs\api-$(Get-Date -Format yyyyMMdd).log"

Write-Host "Starting API on http://$Host:$Port  (AUTH_TOKEN=$($env:AUTH_TOKEN))"
uvicorn satyagrah.web.jobs_api:create_app --factory --host $Host --port $Port --reload *>&1 |
  Tee-Object -FilePath $log
