# scripts/cleanup.ps1
param(
  [int]$KeepDays = 7
)
$ErrorActionPreference = 'Stop'

# move to repo root
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

Write-Host "Root: $root"

# prune old exports (keep today and recent)
$today = Get-Date -Format 'yyyy-MM-dd'
$exports = Join-Path $root 'exports'
if (Test-Path $exports) {
  Get-ChildItem $exports -Directory |
    Where-Object {
      $_.Name -ne $today -and
      ($_.LastWriteTime -lt (Get-Date).AddDays(-$KeepDays))
    } |
    ForEach-Object {
      Write-Host "Deleting $($_.FullName)"
      Remove-Item $_.FullName -Recurse -Force
    }
}

# VACUUM sqlite DB (state.db)
$code = @'
import sqlite3, pathlib
db = pathlib.Path("state.db")
if db.exists():
    con = sqlite3.connect(db)
    con.execute("VACUUM")
    con.close()
print("OK: vacuumed")
'@

$tmp = New-TemporaryFile
Set-Content -Path $tmp -Value $code -Encoding UTF8
python $tmp
Remove-Item $tmp -Force

Write-Host "Cleanup done."
