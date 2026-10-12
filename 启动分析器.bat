@echo off
chcp 65001 >nul 2>&1
title 文献智能分析器
setlocal
set APP=%~dp0main.py
set VENV_PY=%~dp0.venv\Scripts\python.exe

if exist "%VENV_PY%" (
    set PYTHON_CMD="%VENV_PY%"
) else (
    where py >nul 2>&1
    if errorlevel 1 (
        echo [错误] 未找到 Python 环境，请先运行 install_deps.bat 安装。
        pause
        exit /b 1
    )
    py -3.14 --version >nul 2>&1
    if errorlevel 1 (
        echo [错误] 未检测到 Python 3.14，请安装 Python 3.14 或运行 install_deps.bat。
        pause
        exit /b 1
    )
    set PYTHON_CMD=py -3.14
)

if not exist "%APP%" (
    echo [错误] 未找到 main.py：%APP%
    pause
    exit /b 1
)

echo.
echo === 文献智能分析器 ===
echo 正在启动...
%PYTHON_CMD% "%APP%"
if errorlevel 1 (
    echo.
    echo [错误] 程序运行异常，请运行 install_deps.bat 安装依赖。
    pause
)
