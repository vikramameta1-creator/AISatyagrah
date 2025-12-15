$ErrorActionPreference = "Stop"
if (-not $env:REDIS_URL)  { $env:REDIS_URL  = "redis://127.0.0.1:6379/0" }
$env:RQ_WORKER_CLASS = "rq.SimpleWorker"   # Windows-friendly

New-Item -ItemType Directory -Force -Path "$PSScriptRoot\logs" | Out-Null
$log = Join-Path $PSScriptRoot "logs\worker-$(Get-Date -Format yyyyMMdd).log"

Write-Host "Starting RQ worker on $($env:REDIS_URL) (queue: exports)"
python -m rq.cli worker exports --url $env:REDIS_URL *>&1 |
  Tee-Object -FilePath $log
