# D:\AISatyagrah\scripts\ports.ps1
$ErrorActionPreference = 'Stop'

function Get-PortPids {
  param([int]$Port)
  $pids = @()
  try {
    $conns = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction Stop
    if ($conns) { $pids += ($conns | Select-Object -ExpandProperty OwningProcess) }
  } catch {
    # Fallback to netstat (no admin needed)
    $out = netstat -ano | Select-String -Pattern "LISTENING.*:$Port\s+\d+$"
    foreach ($m in $out) {
      $pidStr = ($m.ToString() -split '\s+')[-1]
      if ($pidStr -match '^\d+$') { $pids += [int]$pidStr }
    }
  }
  ($pids | Sort-Object -Unique)
}

function Stop-PortPids {
  param([int]$Port, [switch]$Force)
  $pids = Get-PortPids -Port $Port
  if (-not $pids -or $pids.Count -eq 0) { return @() }
  $killed = @()
  foreach ($procId in $pids) {
    try {
      if ($Force) {
        Stop-Process -Id $procId -Force -ErrorAction Stop
      } else {
        Stop-Process -Id $procId -ErrorAction Stop
      }
      $killed += $procId
    } catch {
      Write-Warning "Failed to stop PID $procId on port $Port: $_"
    }
  }
  return $killed
}

function Test-PortFree {
  param([int]$Port)
  (Get-PortPids -Port $Port).Count -eq 0
}

function Find-FreePort {
  param([int]$StartPort, [int]$MaxTries = 50)
  $p = $StartPort
  for ($i=0; $i -lt $MaxTries; $i++) {
    if (Test-PortFree -Port $p) { return $p }
    $p++
  }
  throw "No free port found from $StartPort .. +$MaxTries"
}
