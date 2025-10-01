param([int]$KeepDays = 14)
$ErrorActionPreference = "Stop"

$repo = Resolve-Path (Join-Path $PSScriptRoot "..")
$exports = Join-Path $repo "exports"
$cutoff = (Get-Date).AddDays(-$KeepDays)

Get-ChildItem $exports -Directory |
  Where-Object { $_.Name -match '^\d{4}-\d{2}-\d{2}$' -and $_.LastWriteTime -lt $cutoff } |
  Remove-Item -Recurse -Force

& "$repo\.venv\Scripts\Activate.ps1"
python - << 'PY'
import sqlite3, pathlib
db = pathlib.Path("state.db")
if db.exists():
    con = sqlite3.connect(db); con.execute("VACUUM"); con.close()
print("cleanup ok")
PY
