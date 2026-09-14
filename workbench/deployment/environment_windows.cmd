@echo off
rem Session-local runtime settings; no system PATH or registry changes.
for %%I in ("%~dp0..\..") do set "SC_PROJECT_DIR=%%~fI"
set "PYTHONUTF8=1"
set "NUMBA_CACHE_DIR=%SC_PROJECT_DIR%\system2\.cache\numba"
if not exist "%NUMBA_CACHE_DIR%" mkdir "%NUMBA_CACHE_DIR%"
if exist "%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe" set "PATH=%LOCALAPPDATA%\Programs\Tesseract-OCR;%PATH%"
if exist "%ProgramFiles%\Tesseract-OCR\tesseract.exe" set "PATH=%ProgramFiles%\Tesseract-OCR;%PATH%"
for /d %%D in ("%SC_PROJECT_DIR%\..\.tools\native\poppler-*") do if exist "%%~fD\Library\bin\pdftotext.exe" set "PATH=%%~fD\Library\bin;%PATH%"
for /d %%D in ("%SC_PROJECT_DIR%\..\.tools\node-*-win-x64") do if exist "%%~fD\node.exe" set "PATH=%%~fD;%PATH%"
if exist "%SC_PROJECT_DIR%\..\.tools\python\Scripts\uv.exe" set "PATH=%SC_PROJECT_DIR%\..\.tools\python\Scripts;%PATH%"
rem A short-path installation carries portable tools inside its own cache.
for /d %%D in ("%SC_PROJECT_DIR%\workbench\.cache\tools\native\poppler-*") do if exist "%%~fD\Library\bin\pdftotext.exe" set "PATH=%%~fD\Library\bin;%PATH%"
for /d %%D in ("%SC_PROJECT_DIR%\workbench\.cache\tools\node-*-win-x64") do if exist "%%~fD\node.exe" set "PATH=%%~fD;%PATH%"
if exist "%SC_PROJECT_DIR%\workbench\.cache\tools\bin\uv.exe" set "PATH=%SC_PROJECT_DIR%\workbench\.cache\tools\bin;%PATH%"
exit /b 0
