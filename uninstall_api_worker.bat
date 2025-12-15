@echo off
for %%N in ("AISatyagrah-API-Startup" "AISatyagrah-API-Logon" "AISatyagrah-Worker-Startup" "AISatyagrah-Worker-Logon") do (
  schtasks /Delete /TN "%%~N" /F
)
echo Removed all AISatyagrah tasks.