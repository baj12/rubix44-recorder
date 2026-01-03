@echo off
REM Installation script for Rubix Recorder API on Windows

echo Installing Rubix Recorder API...
echo =================================

REM Check if conda is available
where conda >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Conda not found. Please install Anaconda or Miniconda first.
    echo Download from: https://www.anaconda.com/products/distribution
    pause
    exit /b 1
)

REM Create conda environment
echo Creating conda environment...
call conda env create -f environment.yml
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to create conda environment.
    pause
    exit /b 1
)

REM Activate environment and install additional dependencies if needed
echo Activating environment...
call conda activate rubix-recorder-api

REM Create necessary directories
echo Creating directories...
mkdir recordings 2>nul
mkdir logs 2>nul
mkdir config 2>nul

echo.
echo Installation completed successfully!
echo.
echo To start the server:
echo   Double-click start_api_server.bat
echo.
echo To test the installation:
echo   Double-click test_installation.bat
echo.

pause