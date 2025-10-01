@echo off
setlocal EnableExtensions EnableDelayedExpansion

:: =================== Defaults ===================
set "PROJECT=D:\AISatyagrah"
set "WEBPORT=8000"
set "SDPORT=7860"
set "RELOAD=0"      :: 1 = uvicorn autoreload for the web UI
set "RESET=1"       :: 1 = kill any process using the ports first
set "NOBROWSER=0"   :: 1 = don't auto-open the browser

:: =================== Args (key=value) ===================
:: Examples:
::   start_stack.bat webport=8010 sdport=7861
::   start_stack.bat reload=1 nobrowser=1
::   start_stack.bat reset=0
for %%A in (%*) do (
  for /F "tokens=1,2 delims==" %%K in ("%%~A") do (
    set "k=%%~K"
    set "v=%%~L"
    if /I "!k!"=="webport"   set "WEBPORT=!v!"
    if /I "!k!"=="sdport"    set "SDPORT=!v!"
    if /I "!k!"=="reload"    set "RELOAD=!v!"
    if /I "!k!"=="reset"     set "RESET=!v!"
    if /I "!k!"=="nobrowser" set "NOBROWSER=!v!"
  )
)

:: =================== Python / env ===================
set "SATY_ROOT=%PROJECT%"
set "PY=%PROJECT%\.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"

pushd "%PROJECT%" >nul 2>&1

call :ensure_deps

:: =================== Free ports (optional) ===================
if "%RESET%"=="1" (
  call :free_port %WEBPORT%
  call :free_port %SDPORT%
)

:: =================== Launch servers ===================
set "RELOADFLAG="
if "%RELOAD%"=="1" set "RELOADFLAG=--reload"

echo.
echo === Starting SD mock on http://127.0.0.1:%SDPORT%/ ===
start "Saty SD Mock (:%SDPORT%)" "%PY%" -m uvicorn satyagrah.mock_sdapi:app --host 127.0.0.1 --port %SDPORT%

echo.
echo === Starting Web UI on http://127.0.0.1:%WEBPORT%/ ===
start "Saty Web UI (:%WEBPORT%)" "%PY%" "%PROJECT%\saty_web.py" --host 127.0.0.1 --port %WEBPORT% %RELOADFLAG%

if not "%NOBROWSER%"=="1" (
  set "URL=http://127.0.0.1:%WEBPORT%/"
  start "Open Web UI" powershell -NoProfile -Command ^
    "for($i=0;$i -lt 40;$i++){try{Invoke-WebRequest -Uri '%URL%' -UseBasicParsing -TimeoutSec 1 ^> $null; start '%URL%'; break}catch{}; Start-Sleep -Milliseconds 500}"
)

echo.
echo Done. (web:%WEBPORT%, sd:%SDPORT%)
popd
endlocal
goto :eof

:: =================== Helpers ===================

:ensure_deps
"%PY%" -c "import fastapi, uvicorn" 1>nul 2>nul || (
  echo [info] Installing fastapi/uvicorn once...
  "%PY%" -m pip install -q -U fastapi uvicorn
)
exit /b 0

:free_port
set "_PORT=%~1"
if "%_PORT%"=="" exit /b 0
set "PIDS="
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":%_PORT% " ^| findstr LISTENING') do (
  set "PIDS=!PIDS! %%P"
)
if not defined PIDS exit /b 0
set "SEEN= "
for %%P in (!PIDS!) do (
  echo !SEEN! | find " %%P " >nul || (
    set "SEEN=!SEEN!%%P "
    echo [info] Freeing port %_PORT% (PID %%P)...
    taskkill /F /PID %%P >nul 2>nul
  )
)
exit /b 0
