@echo off
cd /d "%~dp0"
py -3 "%~dp0deployment.py" %*
if errorlevel 1 pause
