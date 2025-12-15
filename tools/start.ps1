[CmdletBinding()]
param(
  [string]$Bind = '127.0.0.1',
  [int]$Port = 9000,
  [switch]$KillBusyPorts,
  [string]$Token = ''
)

function Get-PortPids([int]$Port) {
  try {
    (Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction Stop |
      Select-Object -ExpandProperty OwningProcess -Unique)
  } catch { @() }
}

if ($KillBusyPorts) {
  $portPids = @(Get-PortPids $Port)
  foreach ($procId in $portPids) {
    try {
      Stop-Process -Id ([int]$procId) -Force -ErrorAction Stop
      Write-Host "Killed PID $procId on $Port" -ForegroundColor DarkYellow
    } catch {
      Write-Host "Could not kill ${procId}: $($_.Exception.Message)" -ForegroundColor Yellow
    }
  }
}

if ($Token) { $env:AUTH_TOKEN = $Token }

$cmd = "uvicorn satyagrah.web.asgi:app --host $Bind --port $Port --reload --log-level info"
Write-Host "Starting: $cmd"
& uvicorn satyagrah.web.asgi:app --host $Bind --port $Port --reload --log-level info
