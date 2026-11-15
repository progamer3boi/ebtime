@echo off
setlocal
set "EBTIME_FUSION=%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion"
if not exist "%EBTIME_FUSION%\ebtime\runtime\Scripts\python.exe" goto missing
"%EBTIME_FUSION%\ebtime\runtime\Scripts\python.exe" "%EBTIME_FUSION%\Scripts\Comp\ebtime_app\app.py"
if errorlevel 1 pause
exit /b
:missing
echo Run Install Windows.cmd first.
pause
