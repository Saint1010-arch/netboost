@echo off
cd /d "%~dp0"

:: NetBoost ?????
:: ???? Python ??? NetBoost

:: ??? py launcher (??????)
py -3 --version >nul 2>&1
if %errorlevel%==0 (
    py -3 -c "import tkinter" >nul 2>&1
    if %errorlevel%==0 (
        start "" py -3 netboost.py
    ) else (
        py -3 netboost.py --cli
        pause
    )
    exit /b
)

:: ???? python
python --version >nul 2>&1
if %errorlevel%==0 (
    python -c "import tkinter" >nul 2>&1
    if %errorlevel%==0 (
        start "" python netboost.py
    ) else (
        python netboost.py --cli
        pause
    )
    exit /b
)

:: ??? - ????
echo.
echo  ============================================
echo.
echo     NetBoost ?? Python ????
echo.
echo     ???????????:
echo     https://www.python.org/downloads/
echo.
echo     ?????? "Add Python to PATH"
echo     ?????????????
echo.
echo  ============================================
echo.
start https://www.python.org/downloads/
pause
