@echo off
setlocal
set ROOT=%~dp0
set API=%ROOT%run_api.ps1
set WORK=%ROOT%run_worker.ps1

if not exist "%API%"  echo ERROR: %API% missing & exit /b 1
if not exist "%WORK%" echo ERROR: %WORK% missing & exit /b 1

schtasks /Delete /TN "AISatyagrah_API"    /F >nul 2>&1
schtasks /Delete /TN "AISatyagrah_Worker" /F >nul 2>&1

schtasks /Create /TN "AISatyagrah_API" /SC ONSTART /RL HIGHEST ^
 /TR "powershell -NoProfile -ExecutionPolicy Bypass -File \"%API%\"" /F

schtasks /Create /TN "AISatyagrah_Worker" /SC ONSTART /RL HIGHEST ^
 /TR "powershell -NoProfile -ExecutionPolicy Bypass -File \"%WORK%\"" /F

echo Installed tasks.
schtasks /Run /TN "AISatyagrah_API"
schtasks /Run /TN "AISatyagrah_Worker"
endlocal
