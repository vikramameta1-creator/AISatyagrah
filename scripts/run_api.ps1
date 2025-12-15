# Runs AISatyagrah Jobs API and restarts it if it exits.
# Logs: D:\AISatyagrah\logs\api-YYYYMMDD.log
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$RepoRoot = Split-Path $PSScriptRoot -Parent
$Venv     = Join-Path $RepoRoot '.venv'
$Py       = Join-Path $Venv 'Scripts\python.exe'
$LogDir   = Join-Path $RepoRoot 'logs'
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$LogFile  = Join-Path $LogDir ("api-{0}.log" -f (Get-Date -Format 'yyyyMMdd'))

# ---- environment (edit as you like) ----
$env:AUTH_TOKEN = if ($env:AUTH_TOKEN) { $env:AUTH_TOKEN } else { 'mysupersecrettoken' }
$env:REDIS_URL  = if ($env:REDIS_URL)  { $env:REDIS_URL }  else { 'redis://127.0.0.1:6379/0' }
$env:JWT_ENABLED = if ($env:JWT_ENABLED) { $env:JWT_ENABLED } else { 'false' }
$env:DEBUG = if ($env:DEBUG) { $env:DEBUG } else { 'false' }

Write-Output "[$(Get-Date -Format o)] starting API watchdog" | Tee-Object -FilePath $LogFile -Append | Out-Null
while ($true) {
  try {
    & $Py -m uvicorn `
        satyagrah.web.jobs_api:create_app `
        --factory --host 127.0.0.1 --port 9000 --workers 1 --no-access-log `
        2>&1 | Tee-Object -FilePath $LogFile -Append
    $code = $LASTEXITCODE
    Write-Output "[$(Get-Date -Format o)] API exited with $code, restarting in 3s" | Tee-Object -FilePath $LogFile -Append | Out-Null
  } catch {
    $_ | Out-String | Tee-Object -FilePath $LogFile -Append | Out-Null
    Write-Output "[$(Get-Date -Format o)] exception, restarting in 3s" | Tee-Object -FilePath $LogFile -Append | Out-Null
  }
  Start-Sleep -Seconds 3
}
