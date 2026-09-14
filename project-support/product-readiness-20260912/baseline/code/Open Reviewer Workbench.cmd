@echo off
setlocal
rem Offline reviewer data is separate from normal workbench/runtime.
call "%~dp0Open Workbench.cmd" --reviewer --root "%~dp0reviewer-workspace" %*
exit /b %errorlevel%
