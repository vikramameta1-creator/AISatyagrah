[CmdletBinding()]
param([int]$Port = 9000)

function Get-PortPids([int]$Port) {
  try {
    (Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction Stop |
      Select-Object -ExpandProperty OwningProcess -Unique)
  } catch { @() }
}

$pids = @(Get-PortPids $Port)
if (-not $pids.Count) {
  Write-Host "Nothing listening on port $Port."
  exit 0
}

foreach ($procId in $pids) {
  try {
    Stop-Process -Id ([int]$procId) -Force -ErrorAction Stop
    Write-Host "Killed PID $procId on $Port"
  } catch {
    Write-Host "Could not kill ${procId}: $($_.Exception.Message)" -ForegroundColor Yellow
  }
}
