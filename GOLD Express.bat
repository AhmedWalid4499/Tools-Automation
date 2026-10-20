@echo off
rem Double-click to start GOLD Express (from the Python source; the shareable app is dist\GOLD Express.exe).
cd /d "%~dp0"
start "" "%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe" gold_app.py
