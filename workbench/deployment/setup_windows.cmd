@echo off
setlocal
call "%~dp0environment_windows.cmd"
set "PYTHONUTF8=1"
rem Explicit setup only: creates component environments, never starts a service.
for %%I in ("%~dp0..\..") do set "PROJECT_DIR=%%~fI"
where py >nul 2>nul
if errorlevel 1 (
  echo Install Python 3.12 with the Windows py launcher, then rerun this setup.
  exit /b 2
)
if exist "%PROJECT_DIR%\..\.tools\python\Scripts\uv.exe" set "PATH=%PROJECT_DIR%\..\.tools\python\Scripts;%PATH%"
where uv >nul 2>nul
if errorlevel 1 (
  echo uv is required to recreate the locked System2 environment. See ENVIRONMENT.md.
  exit /b 2
)
py -3.12 -m venv "%PROJECT_DIR%\workbench\.venv" --without-pip
if errorlevel 1 exit /b %errorlevel%
uv pip install --python "%PROJECT_DIR%\workbench\.venv\Scripts\python.exe" -r "%PROJECT_DIR%\workbench\pyproject.toml"
if errorlevel 1 exit /b %errorlevel%
cd /d "%PROJECT_DIR%\system2"
set "UV_CACHE_DIR=%CD%\.cache\uv"
uv sync --locked --python 3.12 --no-editable
if errorlevel 1 exit /b %errorlevel%
echo Offline reviewer environments are ready for platform checks. No service was started.
echo Coordinator System1 setup is separate; follow ENVIRONMENT.md.
exit /b 0
