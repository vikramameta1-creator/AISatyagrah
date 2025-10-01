@echo off
setlocal EnableExtensions EnableDelayedExpansion
set "PROJECT=D:\AISatyagrah"
set "PY=%PROJECT%\.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"

:: defaults
set "HOST=127.0.0.1"
set "PORT=7860"
set "NOBROWSER=0"

:: parse key=value args
for %%A in (%*) do (
  for /F "tokens=1,2 delims==" %%K in ("%%~A") do (
    if /I "%%~K"=="host"      set "HOST=%%~L"
    if /I "%%~K"=="port"      set "PORT=%%~L"
    if /I "%%~K"=="nobrowser" set "NOBROWSER=%%~L"
  )
)

pushd "%PROJECT%"
"%PY%" -c "import fastapi, uvicorn" 1>nul 2>nul || "%PY%" -m pip install -q -U fastapi uvicorn

echo Starting SD mock API on http://%HOST%:%PORT%/ ...
if not "%NOBROWSER%"=="1" start "" "http://%HOST%:%PORT%/"
"%PY%" -m uvicorn satyagrah.mock_sdapi:app --host %HOST% --port %PORT%
popd
endlocal
