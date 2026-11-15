@echo off
setlocal
cd /d "%~dp0"
echo.
echo  ebtime / @epicbloxfx
echo  Close DaVinci Resolve before installing.
echo.
where py >nul 2>nul
if errorlevel 1 goto usepython
py -3 install.py
if errorlevel 1 goto failed
goto done
:usepython
where python >nul 2>nul
if errorlevel 1 goto missing
python install.py
if errorlevel 1 goto failed
goto done
:missing
echo Install Python 3.11 or 3.12 from https://www.python.org/downloads/windows/
echo Select "Add Python to PATH", then run this installer again.
goto done
:failed
echo.
echo Installation did not finish. Read the error above.
echo Use Python from python.org and check your internet connection.
:done
echo.
pause
