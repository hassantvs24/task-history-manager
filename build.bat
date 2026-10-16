@echo off
REM Rebuild the portable exe (requires .venv from the first build)
cd /d "%~dp0"
.venv\Scripts\python.exe -m PyInstaller --onefile --windowed --name "Task History Manager" app.py
copy /y tasks.json dist\tasks.json
echo.
echo Done: dist\Task History Manager.exe
pause
