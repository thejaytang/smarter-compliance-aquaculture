@echo off
setlocal
rem Offline reviewer data is separate from normal workbench/runtime.
for %%I in ("%~dp0..\..") do set "PROJECT_DIR=%%~fI"
call "%~dp0Open Workbench.cmd" --reviewer --root "%PROJECT_DIR%\reviewer-workspace" %*
exit /b %errorlevel%
