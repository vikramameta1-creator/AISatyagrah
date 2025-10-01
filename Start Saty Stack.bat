@echo off
setlocal EnableExtensions
set "PROJECT=D:\AISatyagrah"
set "PS=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
"%PS%" -NoProfile -ExecutionPolicy Bypass -File "%PROJECT%\start_saty_stack.ps1"
endlocal
