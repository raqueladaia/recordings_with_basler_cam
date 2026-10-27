@echo off
REM MultiCam Recorder launcher (when running from the source code)
REM Double-click this file to start the application

echo ========================================
echo MultiCam Recorder
echo ========================================
echo.

REM Change to the directory where this batch file is located
cd /d "%~dp0"

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found!
    echo.
    echo Please run the setup first:
    echo 1. Open Command Prompt in this folder
    echo 2. Run: python -m venv venv
    echo 3. Run: venv\Scripts\activate
    echo 4. Run: pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate

REM Check if activation worked
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    echo.
    pause
    exit /b 1
)

echo Virtual environment activated!
echo.

REM Check if dependencies are installed
echo Checking dependencies...
python -c "import pypylon" 2>nul
if errorlevel 1 (
    echo ERROR: pypylon not installed!
    echo.
    echo Please install dependencies:
    echo Run: pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

REM Start the application
echo Starting application...
echo DO NOT CLOSE THIS WINDOW WHILE RECORDING. To quit, close the application window.
echo.
python main.py

REM If application exits, show error if any
if errorlevel 1 (
    echo.
    echo ========================================
    echo Application exited with an error
    echo ========================================
    echo.
)

echo.
echo Application closed.
pause
