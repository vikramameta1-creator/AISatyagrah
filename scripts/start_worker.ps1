param([double]$Interval = 1.2)
$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $RepoRoot

& ".\.venv\Scripts\Activate.ps1"
python -m satyagrah.services.worker_loop --interval $Interval
