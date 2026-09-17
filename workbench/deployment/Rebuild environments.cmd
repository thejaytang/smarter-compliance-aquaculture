@echo off
setlocal
call "%~dp0environment_windows.cmd"
set "PYTHONUTF8=1"
py -3.12 "%~dp0rebuild_environments.py" %*
exit /b %errorlevel%
