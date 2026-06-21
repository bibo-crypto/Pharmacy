@echo off
title Pharmacy Build
setlocal enabledelayedexpansion

echo.
echo ===========================================
echo   Pharmacy Management System - Build
echo ===========================================
echo.

REM --- Check Python ---
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found.
    echo Install Python 3.10+ from https://www.python.org
    echo Check "Add Python to PATH" during install.
    pause & exit /b 1
)
for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo [OK] %%v

REM --- Python version check: must be 3.10 or higher ---
python -c "import sys; exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 3.10 or higher required.
    python --version
    pause & exit /b 1
)
echo [OK] Python version OK

REM --- Create venv ---
if not exist "venv\" (
    echo [INFO] Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create venv.
        pause & exit /b 1
    )
    echo [OK] venv created.
) else (
    echo [OK] venv exists.
)

REM --- Activate venv ---
call venv\Scripts\activate.bat
echo [OK] venv activated.

REM --- Upgrade pip ---
echo [INFO] Upgrading pip...
python -m pip install --upgrade pip -q
echo [OK] pip upgraded.

REM --- Install requirements ---
echo [INFO] Installing requirements...
pip install -r requirements.txt -q
if errorlevel 1 (
    echo [ERROR] pip install failed. Check requirements.txt
    call venv\Scripts\deactivate.bat
    pause & exit /b 1
)
echo [OK] Requirements installed.

REM --- Install PyInstaller ---
echo [INFO] Installing PyInstaller...
pip install "pyinstaller>=6.0" -q
if errorlevel 1 (
    echo [ERROR] PyInstaller install failed.
    call venv\Scripts\deactivate.bat
    pause & exit /b 1
)
echo [OK] PyInstaller ready.

REM --- Check icon ---
set USE_SPEC=pharmacy.spec
if not exist "assets\icon.ico" (
    echo [WARN] assets\icon.ico not found - building without icon.
) else (
    echo [OK] Icon found.
)

REM --- Clean old build ---
echo [INFO] Cleaning old build...
if exist "dist\" rmdir /s /q "dist" >nul 2>&1
if exist "build\" rmdir /s /q "build" >nul 2>&1
echo [OK] Cleaned.

REM --- Run PyInstaller ---
echo.
echo [INFO] Building... (this takes 5-10 minutes)
echo.
python -m PyInstaller %USE_SPEC% --noconfirm --clean
set RESULT=%errorlevel%

if exist "_build_noicon.spec" del "_build_noicon.spec" >nul 2>&1

if %RESULT% neq 0 (
    echo.
    echo [ERROR] Build failed. See output above.
    call venv\Scripts\deactivate.bat
    pause & exit /b 1
)

REM --- Verify result ---
if exist "dist\pharmacy\pharmacy.exe" (
    echo.
    echo ===========================================
    echo [OK] Build complete!
    echo.
    echo EXE: dist\pharmacy\pharmacy.exe
    echo.
    echo Next step - create installer:
    echo   Open Inno Setup Compiler
    echo   File ^> Open ^> installer.iss
    echo   Press F9 to build
    echo   Output: output\pharmacy_setup_v1.0.0.exe
    echo ===========================================
) else (
    echo [ERROR] pharmacy.exe not found after build.
)

call venv\Scripts\deactivate.bat
echo.
pause
