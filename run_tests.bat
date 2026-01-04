@echo off
REM Run tests inside the rubix-recorder-api conda environment
echo Installing pytest into conda environment (if missing)...
conda run -n rubix-recorder-api python -m pip install pytest -q
echo Running pytest...
conda run -n rubix-recorder-api python -m pytest -q %*
if %ERRORLEVEL% NEQ 0 (
  echo Test run finished with errors.
  exit /b %ERRORLEVEL%
) else (
  echo All tests passed.
)
