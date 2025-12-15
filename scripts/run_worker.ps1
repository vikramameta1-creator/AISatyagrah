# Runs the RQ worker and restarts it if it exits.
# Logs: D:\AISatyagrah\logs\worker-YYYYMMDD.log
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$RepoRoot = Split-Path $PSScriptRoot -Parent
$Venv     = Join-Path $RepoRoot '.venv'
$Py       = Join-Path $Venv 'Scripts\python.exe'
$LogDir   = Join-Path $RepoRoot 'logs'
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$LogFile  = Join-Path $LogDir ("worker-{0}.log" -f (Get-Date -Format 'yyyyMMdd'))

# ---- environment ----
$env:REDIS_URL       = if ($env:REDIS_URL) { $env:REDIS_URL } else { 'redis://127.0.0.1:6379/0' }
$env:RQ_WORKER_CLASS = 'rq.SimpleWorker'     # important on Windows
$env:PYTHONUNBUFFERED = '1'

Write-Output "[$(Get-Date -Format o)] starting worker watchdog" | Tee-Object -FilePath $LogFile -Append | Out-Null
while ($true) {
  try {
    & $Py -m rq.cli worker exports --url $env:REDIS_URL 2>&1 | Tee-Object -FilePath $LogFile -Append
    $code = $LASTEXITCODE
    Write-Output "[$(Get-Date -Format o)] worker exited with $code, restarting in 3s" | Tee-Object -FilePath $LogFile -Append | Out-Null
  } catch {
    $_ | Out-String | Tee-Object -FilePath $LogFile -Append | Out-Null
    Write-Output "[$(Get-Date -Format o)] exception, restarting in 3s" | Tee-Object -FilePath $LogFile -Append | Out-Null
  }
  Start-Sleep -Seconds 3
}
