@echo off
setlocal enabledelayedexpansion

echo ==============================================
echo [1/4] Checking Python environment...

rem 尝试定位 python 命令
python --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=python
    goto :found_python
)

python3 --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=python3
    goto :found_python
)

py --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=py
    goto :found_python
)

rem 如果系统路径没有，尝试查找当前目录下的 venv
if exist "%~dp0venv\Scripts\python.exe" (
    echo System python not found, but venv python exists. Using it.
    set PYTHON_CMD="%~dp0venv\Scripts\python.exe"
    goto :skip_venv_creation
)

rem 尝试查找常用的 Windows Python 路径
if exist "C:\Python312\python.exe" (
    set PYTHON_CMD="C:\Python312\python.exe"
    goto :found_python
)
if exist "C:\Python311\python.exe" (
    set PYTHON_CMD="C:\Python311\python.exe"
    goto :found_python
)
if exist "C:\Python310\python.exe" (
    set PYTHON_CMD="C:\Python310\python.exe"
    goto :found_python
)
if exist "C:\Python39\python.exe" (
    set PYTHON_CMD="C:\Python39\python.exe"
    goto :found_python
)
rem 尝试查找 Trae 内置的 uv python 环境
rem 先检查 .local/bin 下的 python3.14.exe
if exist "C:\Users\%USERNAME%\.local\bin\python3.14.exe" (
    set PYTHON_CMD="C:\Users\%USERNAME%\.local\bin\python3.14.exe"
    goto :found_python
)
rem 再尝试查找用户 AppData 下的 uv python
if exist "C:\Users\%USERNAME%\AppData\Roaming\uv\python\cpython-3.14-windows-x86_64-none\python.exe" (
    set PYTHON_CMD="C:\Users\%USERNAME%\AppData\Roaming\uv\python\cpython-3.14-windows-x86_64-none\python.exe"
    goto :found_python
)
rem 如果没有，尝试查找 D 盘或其他常见位置（根据用户环境定制）
if exist "D:\Python\python.exe" (
    set PYTHON_CMD="D:\Python\python.exe"
    goto :found_python
)

echo Error: Python is not installed or not in PATH.
echo Please install Python from python.org or Microsoft Store.
pause
exit /b 1

:found_python
echo Found Python: !PYTHON_CMD!

echo [2/4] Setting up virtual environment...
cd /d "%~dp0"
if not exist "venv" (
    echo Creating new virtual environment...
    !PYTHON_CMD! -m venv venv
) else (
    echo Virtual environment already exists.
)

:skip_venv_creation
echo [3/4] Installing dependencies...
rem 使用 venv 中的 pip
set PIP_CMD="%~dp0venv\Scripts\pip.exe"
if not exist !PIP_CMD! (
    echo Error: pip not found in virtual environment.
    pause
    exit /b 1
)

!PIP_CMD! install --upgrade pip
!PIP_CMD! install -r requirements.txt
!PIP_CMD! install pyinstaller

echo [4/4] Packaging application...
if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"

rem 使用 venv 中的 pyinstaller
set PYINSTALLER_CMD="%~dp0venv\Scripts\pyinstaller.exe"

if not exist !PYINSTALLER_CMD! (
    echo Error: PyInstaller not found. Installation might have failed.
    pause
    exit /b 1
)

rem 确保在 main.py 所在的目录下执行
if not exist "main.py" (
    echo Error: main.py not found in current directory: %CD%
    echo Please make sure you are running this script from the project root.
    pause
    exit /b 1
)

!PYINSTALLER_CMD! --noconsole --onefile --clean --name="MoonDanceSimulator" main.py --add-data "src;src"

echo.
echo ==============================================
echo Packaging complete!
if exist "dist\MoonDanceSimulator.exe" (
    echo The executable file is ready at:
    echo %CD%\dist\MoonDanceSimulator.exe
) else (
    echo Error: Packaging failed. Check the output above for errors.
)
echo ==============================================
pause
