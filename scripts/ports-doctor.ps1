param([int[]]$Ports=@(8000,9000))
$ErrorActionPreference = "Continue"
foreach($p in $Ports){
  $conns = Get-NetTCPConnection -State Listen -LocalPort $p -ErrorAction SilentlyContinue
  if($conns){
    Write-Host "Port $p is in use by PIDs: " -NoNewline
    $conns | Select -Expand OwningProcess -Unique | ForEach-Object { Write-Host $_ -NoNewline; Write-Host " " -NoNewline }
    Write-Host
    foreach($pid in ($conns | Select -Expand OwningProcess -Unique)){
      try{ Stop-Process -Id $pid -Force -ErrorAction Stop; Write-Host "Stopped PID $pid on $p" }
      catch{ Write-Warning "Could not stop PID $pid on $p ($_)" }
    }
  } else {
    Write-Host "Port $p is free."
  }
}
