@echo off
REM Quick fix for NumPy AVX2 compatibility issue on older CPUs
REM This script downgrades NumPy to version 1.26.4 which works with AVX (not AVX2)

echo ===============================================
echo NumPy Compatibility Fix for Older CPUs
echo ===============================================
echo.
echo Your CPU: Intel Core i7-3610QM (Ivy Bridge, 2012)
echo Supports: AVX (but NOT AVX2)
echo.
echo NumPy 2.x requires AVX2, causing "illegal instruction" errors
echo This script will downgrade to NumPy 1.26.4 (AVX compatible)
echo.
echo ===============================================
echo.

REM Activate conda environment
echo Activating conda environment...
call conda activate rubix-recorder-api
if errorlevel 1 (
    echo ERROR: Could not activate rubix-recorder-api environment
    echo Please ensure conda is installed and the environment exists
    pause
    exit /b 1
)

echo.
echo Uninstalling NumPy 2.x...
pip uninstall -y numpy

echo.
echo Installing NumPy 1.26.4 (AVX compatible)...
pip install numpy==1.26.4

echo.
echo ===============================================
echo Verification
echo ===============================================
echo.

echo Testing NumPy import...
python -c "import numpy; print(f'SUCCESS: NumPy {numpy.__version__} loaded')"
if errorlevel 1 (
    echo ERROR: NumPy import failed
    pause
    exit /b 1
)

echo.
echo Testing all required modules...
python -c "import numpy; import scipy; import sounddevice; import soundfile; print('SUCCESS: All modules loaded correctly')"
if errorlevel 1 (
    echo ERROR: Module import failed
    pause
    exit /b 1
)

echo.
echo ===============================================
echo Fix Complete!
echo ===============================================
echo.
echo NumPy has been downgraded to 1.26.4 (AVX compatible)
echo You can now start the API server:
echo.
echo     python api_server.py
echo.
pause
