@echo off
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed. Exiting...
    pause
    exit /b
)
echo Python is installed. Installing packages from requirements.txt...
pip install -r requirements.txt
pause
