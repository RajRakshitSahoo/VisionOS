@echo off
title VisionOS AI
echo.
echo  ================================================
echo   VisionOS AI - Hands-Free Computer Control
echo  ================================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  ERROR: Python not found!
    echo  Please install Python 3.10 from https://www.python.org
    echo  Make sure to check "Add Python to PATH" during install.
    pause
    exit /b 1
)

:: Check if dependencies are installed
python -c "import cv2, mediapipe, customtkinter" >nul 2>&1
if %errorlevel% neq 0 (
    echo  Installing dependencies...
    echo.
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo.
        echo  ERROR: Failed to install dependencies.
        echo  Try running: pip install -r requirements.txt
        pause
        exit /b 1
    )
)

echo  Starting VisionOS AI...
echo.
python app.py

if %errorlevel% neq 0 (
    echo.
    echo  VisionOS AI exited with an error.
    echo  Check the log at: %USERPROFILE%\.visionos_ai\visionos.log
    pause
)
