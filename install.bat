 @echo off
title VisionOS AI - Installer
echo.
echo  ================================================
echo   VisionOS AI - Dependency Installer
echo  ================================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  ERROR: Python not found.
    echo  Download from: https://www.python.org/downloads/
    echo  Install Python 3.10 and check "Add Python to PATH"
    pause
    exit /b 1
)

echo  Python found. Installing packages...
echo.

pip install --upgrade pip
pip install opencv-python>=4.8.0
pip install mediapipe>=0.10.0
pip install customtkinter>=5.2.0
pip install Pillow>=10.0.0
pip install numpy>=1.24.0
pip install pyautogui>=0.9.54
pip install pynput>=1.7.6
pip install screeninfo>=0.8.1
pip install psutil>=5.9.0
pip install SQLAlchemy>=2.0.0
pip install pywin32>=306
pip install screen-brightness-control>=0.23.0

echo.
echo  Trying optional audio packages...
pip install pycaw comtypes >nul 2>&1

echo.
echo  ================================================
echo   Installation complete!
echo   Run VisionOS AI with: run.bat or python app.py
echo  ================================================
echo.
pause
