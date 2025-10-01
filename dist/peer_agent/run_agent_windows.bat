@echo off
setlocal
REM --- Paths (relative to this folder) ---
set ROOT=%~dp0
set INBOX=%ROOT%inbox
set OUTBOX=%ROOT%out
set STATE=%ROOT%agent_state.db
set CFG=%ROOT%agent_config.json
set SDHOST=

if "%SATYAGRAH_SECRET%"=="" (
  echo [ERROR] SATYAGRAH_SECRET is not set. See README.txt
  pause
  exit /b 1
)

REM ensure folders
if not exist "%INBOX%" mkdir "%INBOX%"
if not exist "%OUTBOX%" mkdir "%OUTBOX%"

python -m satyagrah.peer.agent run --inbox "%INBOX%" --outbox "%OUTBOX%" --state "%STATE%" --config "%CFG%" --panel-port 8090 %SDHOST%
pause
