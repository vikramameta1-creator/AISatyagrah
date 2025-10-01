@'
@echo off
echo This will DELETE D:\AISatyagrah permanently. Press Ctrl+C to cancel.
pause
set "TARGET=D:\AISatyagrah"
set "HELPER=%TEMP%\aisatyagrah_uninstall_helper.bat"
> "%HELPER%" echo @echo off
>> "%HELPER%" echo ping 127.0.0.1 -n 2 ^>nul
>> "%HELPER%" echo rmdir /S /Q "%TARGET%"
>> "%HELPER%" echo del "%%~f0"
start "" "%HELPER%"
exit
'@ > uninstall.bat
