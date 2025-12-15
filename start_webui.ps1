$ErrorActionPreference = "Stop"
Push-Location $PSScriptRoot
try {
  if (-not (Test-Path .\.venv\Scripts\Activate.ps1)) {
    throw "Virtualenv not found at .\.venv. Create it first."
  }
  .\.venv\Scripts\Activate.ps1
  # Optional: disable auth for local testing
  # $env:AUTH_TOKEN = ""
  Write-Host "Starting AISatyagrah web on http://127.0.0.1:9000 ..."
  python -m uvicorn satyagrah.web.jobs_api:app --host 127.0.0.1 --port 9000 --reload
} finally {
  Pop-Location
}
