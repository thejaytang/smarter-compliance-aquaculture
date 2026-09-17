@echo off
setlocal
for %%I in ("%~dp0..\..") do set "PROJECT_DIR=%%~fI\"
set "WORKBENCH_DIR=%PROJECT_DIR%workbench"
if not exist "%WORKBENCH_DIR%\.venv\Scripts\python.exe" (
  echo The local workbench environment is missing. Follow ENVIRONMENT.md.
  exit /b 2
)
set "PYTHONPATH=%WORKBENCH_DIR%\src"
cd /d "%WORKBENCH_DIR%"
"%WORKBENCH_DIR%\.venv\Scripts\python.exe" -m local_workbench %*
exit /b %errorlevel%
