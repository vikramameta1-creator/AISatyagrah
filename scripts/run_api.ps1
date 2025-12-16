param([int]$Port = 9000)

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $root

# Prefer token from .auth_token (not committed)
if (Test-Path ".auth_token") {
  $env:AUTH_TOKEN = (Get-Content ".auth_token" -Raw).Trim()
  Write-Host "[run_api] AUTH_TOKEN loaded from .auth_token"
} else {
  Remove-Item Env:\AUTH_TOKEN -ErrorAction SilentlyContinue
  Write-Host "[run_api] No .auth_token found; AUTH disabled"
}

Remove-Item Env:\JWT_SECRET -ErrorAction SilentlyContinue

uvicorn satyagrah.web.jobs_api:app --host 127.0.0.1 --port $Port --reload
