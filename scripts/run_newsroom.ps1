param(
    [string]$Date = ""
)

$ErrorActionPreference = "Stop"

# 1) cd + venv
Set-Location "D:\AISatyagrah"
if (-not (Test-Path ".\.venv\Scripts\activate")) {
    Write-Error "Virtual env not found at .\.venv. Activate it first."
}
. .\.venv\Scripts\activate

# 2) Build newsroom plan for telegram
$newsroomArgs = @("newsroom", "--platform", "telegram")
if ($Date) {
    $newsroomArgs += @("--date", $Date)
}

Write-Host "[run_newsroom] Building plan: satyagrah $($newsroomArgs -join ' ')"
python -m satyagrah @newsroomArgs

# 3) Start Jobs API if not already running on 9000
$port = 9000
$inUse = (Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue)
if (-not $inUse) {
    Write-Host "[run_newsroom] Starting Jobs API on port $port"
    Start-Process powershell -ArgumentList @(
        "-NoExit",
        "-Command",
        "cd D:\AISatyagrah; . .\.venv\Scripts\activate; uvicorn satyagrah.web.jobs_api:create_app --factory --host 127.0.0.1 --port 9000 --reload"
    )
} else {
    Write-Host "[run_newsroom] Jobs API already listening on port $port"
}

# 4) Open browser
Start-Process "http://127.0.0.1:9000/ui/newsroom"
