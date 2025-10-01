@echo off
setlocal EnableExtensions
set "PROJECT=D:\AISatyagrah"
set "PY=%PROJECT%\.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"

set "WEBHOST=127.0.0.1"
set "WEBPORT=8000"
set "SDHOST=127.0.0.1"
set "SDPORT=7860"

pushd "%PROJECT%" >nul

REM --- ensure deps for SD mock (quiet) ---
"%PY%" -c "import fastapi, uvicorn" 1>nul 2>nul || "%PY%" -m pip install -q -U fastapi uvicorn

REM --- free ports if busy ---
for %%P in (%SDPORT% %WEBPORT%) do (
  for /f %%K in ('powershell -NoProfile -Command ^
    "(Get-NetTCPConnection -LocalPort %%P -State Listen -ErrorAction SilentlyContinue | Select -Expand OwningProcess) -join ''"') do (
    if not "%%K"=="" taskkill /F /PID %%K >nul 2>nul
  )
)

REM --- start SD mock (7860) in its own window ---
start "SD API :%SDPORT%" "%PY%" -m uvicorn satyagrah.mock_sdapi:app --host %SDHOST% --port %SDPORT%
start "" "http://%SDHOST%:%SDPORT%/docs"

REM --- start Web UI (8000) in its own window ---
start "Satyagrah UI :%WEBPORT%" "%PY%" "%PROJECT%\saty_web.py" --host %WEBHOST% --port %WEBPORT%
start "" "http://%WEBHOST%:%WEBPORT%/"

popd
endlocal
