@echo off
chcp 65001 >nul 2>&1
setlocal
set APP=%~dp0main.py
set VENV_PY=%~dp0.venv\Scripts\python.exe

if not exist "%APP%" (
    echo [错误] 未找到 main.py：%APP%
    pause
    exit /b 1
)

if exist "%VENV_PY%" (
    "%VENV_PY%" "%APP%"
) else (
    py -3.14 "%APP%"
)

if errorlevel 1 (
    echo.
    echo [错误] 程序运行失败，请运行 install_deps.bat 安装依赖。
    pause
)
