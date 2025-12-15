param(
  [string]$Token = "mysupersecrettoken",
  [int]$Port = 9000
)
$ErrorActionPreference = "Stop"
Set-Location "D:\AISatyagrah"
.\.venv\Scripts\Activate.ps1 | Out-Null
# kill anything already listening on this port
Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue |
  Select-Object -Expand OwningProcess -Unique | ForEach-Object {
    try { Stop-Process -Id $_ -Force -ErrorAction Stop } catch {}
  }
$env:AUTH_TOKEN = $Token
uvicorn satyagrah.web.jobs_api:app --host 127.0.0.1 --port $Port --reload
