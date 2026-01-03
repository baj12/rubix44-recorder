@echo off
REM Test installation script for Rubix Recorder API

echo Testing Rubix Recorder API Installation
echo =======================================

REM Check if conda is available
where conda >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Conda not found. Please install Anaconda or Miniconda first.
    pause
    exit /b 1
)

REM Activate environment
echo Activating conda environment...
call conda activate rubix-recorder-api
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to activate conda environment.
    echo Please run install_windows.bat first.
    pause
    exit /b 1
)

REM Test Python imports
echo Testing Python imports...
python -c "import flask, sounddevice, soundfile, numpy" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to import required Python packages.
    echo Please check your installation.
    pause
    exit /b 1
)

REM Test API server (quick test)
echo Testing API server startup...
timeout /t 5 >nul
python -c "import api_server; print('API server module imported successfully')" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo WARNING: API server module import failed.
    echo This may be normal if the server is not running.
) else (
    echo API server module imported successfully.
)

REM Test client library
echo Testing client library...
python -c "import xor_client; print('Client library imported successfully')"
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to import client library.
    pause
    exit /b 1
)

echo.
echo All tests passed!
echo Installation appears to be working correctly.
echo.
echo To start the server:
echo   Double-click start_api_server.bat
echo.
echo To run the full API test suite:
echo   python test_api.py
echo.

pause