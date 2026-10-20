@echo off
rem Builds release\GOLD_Express_Setup_<version>.exe (the file to share).
rem Bump the version in version.py first. Needs Python, PyInstaller and Inno Setup on this PC.
cd /d "%~dp0"
"%LOCALAPPDATA%\Programs\Python\Python312\python.exe" build_release.py
echo.
pause
