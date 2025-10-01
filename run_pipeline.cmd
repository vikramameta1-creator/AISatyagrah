@echo off
setlocal
cd /d D:\AISatyagrah

REM --- activate venv ---
call .\.venv\Scripts\activate.bat

REM --- require bot token in env (you already set it earlier) ---
if not defined SATYAGRAH_TELEGRAM_BOT (
  echo ERROR: Please set SATYAGRAH_TELEGRAM_BOT environment variable first.
  goto :end
)

REM --- chat id for your account/channel ---
set "CHAT_ID=2085614794"

REM 1) fetch + shortlist
python -m satyagrah research
python -m satyagrah triage --date latest --top 3

REM 2) pipeline + jpgs
python -m satyagrah batch --date latest --top 3 --seed 12345 --package --csv --saveas --saveas-dir outbox
python -m satyagrah thumbs --date latest

REM 3) doctor (strict)
python -m satyagrah doctor --strict
if errorlevel 1 goto :end

REM 4) CSV + Telegram
python -m satyagrah socialcsv --date latest
python -m satyagrah telegram --date latest --chat %CHAT_ID% --lang en,hi --delay 1.5

:end
echo Done.
exit /b 0
