@echo off
setlocal EnableExtensions EnableDelayedExpansion
set "PROJECT=D:\AISatyagrah"
set "PY=%PROJECT%\.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"

:: defaults
set "HOST=127.0.0.1"
set "PORT=8000"
set "RELOAD=0"
set "NOBROWSER=0"
set "FORCEFALLBACK=0"
set "OFFLINE=0"

:: parse key=value args
for %%A in (%*) do (
  for /F "tokens=1,2 delims==" %%K in ("%%~A") do (
    if /I "%%~K"=="host"          set "HOST=%%~L"
    if /I "%%~K"=="port"          set "PORT=%%~L"
    if /I "%%~K"=="reload"        set "RELOAD=%%~L"
    if /I "%%~K"=="nobrowser"     set "NOBROWSER=%%~L"
    if /I "%%~K"=="forcefallback" set "FORCEFALLBACK=%%~L"
    if /I "%%~K"=="offline"       set "OFFLINE=%%~L"
  )
)

pushd "%PROJECT%"
set "URL=http://%HOST%:%PORT%/"

if "%OFFLINE%"=="1" (
  echo [info] Offline mode: writing static page...
  "%PY%" "%PROJECT%\saty_web.py" --offline --offline-out "%PROJECT%\saty_offline.html"
  if not "%NOBROWSER%"=="1" start "" "%PROJECT%\saty_offline.html"
  popd & endlocal & exit /b
)

:: if already up, just open it
for /f %%X in ('powershell -NoProfile -Command ^
  "try{(Invoke-WebRequest -Uri ''%URL%'' -UseBasicParsing -TimeoutSec 1) ^> $null; ''UP''}catch{''DOWN''}"') do set "UP=%%X"
if /I "%UP%"=="UP" (
  echo [info] Detected server already running on %URL%
  if not "%NOBROWSER%"=="1" start "" "%URL%"
  popd & endlocal & exit /b
)

set "RELOADFLAG="
if "%RELOAD%"=="1" set "RELOADFLAG=--reload"
set "FFLAG="
if "%FORCEFALLBACK%"=="1" set "FFLAG=--force-fallback"

echo Starting Satyagrah Web UI on %URL% ...
if not "%NOBROWSER%"=="1" (
  start "" cmd /c ^
    "for /L %%i in (1,1,30) do ( ^
        powershell -NoProfile -Command \"try{(Invoke-WebRequest -Uri '%URL%' -UseBasicParsing -TimeoutSec 1) > $null; exit 0}catch{exit 1}\" ^
        & if !errorlevel! equ 0 (start \"\" \"%URL%\" & exit /b 0) ^
        & ping -n 2 127.0.0.1 >nul ^
     )"
)

"%PY%" "%PROJECT%\saty_web.py" --host %HOST% --port %PORT% %RELOADFLAG% %FFLAG%
popd
endlocal
