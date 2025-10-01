param([int]$Port = 9000)
$ErrorActionPreference = "Stop"

# go to repo root from this script's folder
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $RepoRoot

& ".\.venv\Scripts\Activate.ps1"
uvicorn satyagrah.web.jobs_api:app --host 127.0.0.1 --port $Port --reload
