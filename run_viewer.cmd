@echo off
cd /d "%~dp0"

set "PY="
if exist "F:\python10\python.exe" set "PY=F:\python10\python.exe"
if not defined PY for %%I in (python.exe) do set "PY=%%~$PATH:I"
if not defined PY goto nopython
if not exist "viewer2.py" goto noviewer

echo ============================================
echo   Resource viewer  -^>  http://127.0.0.1:8794/
echo   Close this window or press Ctrl+C to stop.
echo ============================================
echo.
"%PY%" viewer2.py --port 8794
echo.
echo Server stopped.
pause
exit /b 0

:nopython
echo ERROR: python.exe not found.
echo Install Python or edit this file to set the full path.
pause
exit /b 1

:noviewer
echo ERROR: viewer2.py not found next to this .cmd
pause
exit /b 1
