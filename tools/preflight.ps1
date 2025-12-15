[CmdletBinding()]
param(
  [int[]]$Ports = @(8010, 7860, 9000)
)

function Get-PortPids {
  param([int]$Port)
  try {
    (Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction Stop |
      Select-Object -ExpandProperty OwningProcess -Unique)
  } catch { @() }
}

Write-Host "=== Preflight ==="
Write-Host "OS       : $([Environment]::OSVersion.VersionString)"
Write-Host "Machine  : $env:COMPUTERNAME"
Write-Host "User     : $env:USERNAME"
Write-Host "Python   : $(Get-Command python -ErrorAction SilentlyContinue | % Source)"
Write-Host "Venv     : $PSScriptRoot\..\ .venv" 
Write-Host "==================`n"

foreach ($p in $Ports) {
  $pids = @(Get-PortPids $p)
  if ($pids.Count) {
    Write-Host "Port $($p): IN USE by PID(s) $($pids -join ', ')" -ForegroundColor Yellow
  } else {
    Write-Host "Port $($p): free" -ForegroundColor Green
  }
}

Write-Host "Preflight done. Ready to start services."
