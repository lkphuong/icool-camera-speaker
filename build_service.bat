@echo off
echo Building Audio Socket Service...

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install requirements
echo Installing requirements...
pip install -r requirements.txt

REM Build the service
echo Building executable...
pyinstaller audio_service.spec

echo.
echo Build complete!
echo Executable location: dist\AudioSocketService.exe
echo.
echo To install the service, run as Administrator:
echo   dist\AudioSocketService.exe install
echo.
echo To start the service:
echo   net start AudioSocketService
echo.
echo To stop the service:
echo   net stop AudioSocketService
echo.
echo To uninstall the service:
echo   dist\AudioSocketService.exe remove

pause
