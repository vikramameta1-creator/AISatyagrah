@echo off
setlocal EnableExtensions
call "%~dp0stop_saty_stack.cmd"
call "%~dp0start_saty_stack.cmd"
endlocal
