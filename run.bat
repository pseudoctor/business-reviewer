@echo off
REM Pseudoctor Business Reviewer - Data Processing Script (Windows)

setlocal enabledelayedexpansion

cd /d "%~dp0"

echo ==========================================
echo  Pseudoctor Business Reviewer
echo  Data Processing Pipeline
echo ==========================================

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Install dependencies if needed
if not exist "venv\" (
    echo.
    echo [Setup] Creating virtual environment...
    python -m venv venv
    call venv\Scripts\activate.bat
    python -m pip install --upgrade pip
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate.bat
)

REM Keep environment in sync with requirements
pip install -r requirements.txt

REM Run data processor
echo.
echo [Processing] Running data processor...
python scripts\data_processor.py %*

REM Generate final report with embedded data
echo.
echo [Reporting] Building full HTML report...
python scripts\create_final_report.py %*

REM Check if data was generated
if exist "data\analysis_data.json" (
    echo.
    echo ==========================================
    echo  SUCCESS!
    echo ==========================================
    echo Data file: data\analysis_data.json
    echo Report:    reports\report_with_data.html
    echo.
    echo To view the report, open the HTML file in your browser.
) else (
    echo.
    echo Error: Data file was not generated
    pause
    exit /b 1
)

pause
