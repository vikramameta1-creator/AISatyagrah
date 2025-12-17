# scripts/run_server_noauth.ps1
param(
  [string]$Bind = "127.0.0.1",
  [int]$Port = 9000,
  [switch]$Reload
)

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
& "$root\scripts\run_server.ps1" -NoAuth -Bind $Bind -Port $Port -Reload:$Reload
