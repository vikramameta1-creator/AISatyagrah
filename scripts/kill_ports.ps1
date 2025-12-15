param([int[]]$Ports = @(9000,7860,8010,8000))

$ErrorActionPreference = "SilentlyContinue"

foreach ($p in $Ports) {
  $conns = Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue
  if (-not $conns) {
    Write-Host "Port $p: free" -ForegroundColor DarkGray
    continue
  }
  $pids = $conns | Select-Object -ExpandProperty OwningProcess -Unique
  foreach ($pid in $pids) {
    try {
      $proc = Get-Process -Id $pid -ErrorAction Stop
      Write-Host "Killing PID $pid ($($proc.ProcessName)) on port $p" -ForegroundColor Yellow
      Stop-Process -Id $pid -Force
    } catch {
      Write-Host "Could not kill PID $pid on port $p" -ForegroundColor Red
    }
  }
}
