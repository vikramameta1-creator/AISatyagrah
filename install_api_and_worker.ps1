# Save as install_api_and_worker.ps1 and run as Admin
$root = (Resolve-Path .).Path
$python = Join-Path $root ".venv\Scripts\python.exe"
$uvicorn = Join-Path $root ".venv\Scripts\uvicorn.exe"
$env:AUTH_TOKEN = "mysupersecrettoken"
$env:REDIS_URL  = "redis://127.0.0.1:6379/0"
$apiArgs = "satyagrah.web.jobs_api:create_app --factory --host 127.0.0.1 --port 9000"
$workerArgs = "-m rq.cli worker exports --url $env:REDIS_URL"
# Register tasks
schtasks /Create /TN AISatyagrah_API /TR "`"$uvicorn`" $apiArgs" /SC ONSTART /RL HIGHEST /F
schtasks /Create /TN AISatyagrah_Worker /TR "`"$python`" $workerArgs" /SC ONSTART /RL HIGHEST /F
schtasks /Run /TN AISatyagrah_API
schtasks /Run /TN AISatyagrah_Worker

