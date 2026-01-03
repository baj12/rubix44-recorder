@echo off
REM Start Rubix Recorder API Server on Windows

echo Starting Rubix Recorder API Server...

REM Check if conda is available
where conda >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Conda not found. Please install Anaconda or Miniconda first.
    pause
    exit /b 1
)

REM Initialize conda for batch usage
call conda init cmd.exe >nul 2>&1

REM Activate the environment
echo Activating conda environment...
call conda activate rubix-recorder-api

REM Check if activation was successful
if %ERRORLEVEL% NEQ 0 (
    echo Creating conda environment from environment.yml...
    call conda env create -f environment.yml
    if %ERRORLEVEL% NEQ 0 (
        echo ERROR: Failed to create conda environment.
        pause
        exit /b 1
    )
    call conda activate rubix-recorder-api
)

REM Start the API server
echo Starting API server...
python api_server.py

pause