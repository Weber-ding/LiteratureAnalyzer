@echo off
chcp 65001 >nul 2>&1
title 依赖安装
setlocal
set VENV=%~dp0.venv

where py >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python 启动器（py），请先安装 Python 3.10 及以上版本。
    pause
    exit /b 1
)

py -3.14 --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python 3.14，请安装 Python 3.14 后再运行本脚本。
    pause
    exit /b 1
)

echo.
echo 正在创建虚拟环境（.venv）...
if not exist "%VENV%\Scripts\python.exe" (
    py -3.14 -m venv "%VENV%"
)

echo.
echo 正在升级 pip...
"%VENV%\Scripts\python.exe" -m pip install --upgrade pip

echo.
echo 正在安装依赖...
"%VENV%\Scripts\pip.exe" install PyMuPDF python-pptx python-docx openai requests beautifulsoup4 shiboken6 PySide6_Essentials -i https://mirrors.aliyun.com/pypi/simple/
if errorlevel 1 (
    echo 阿里云镜像安装失败，尝试使用官方源...
    "%VENV%\Scripts\pip.exe" install PyMuPDF python-pptx python-docx openai requests beautifulsoup4 shiboken6 PySide6_Essentials
)
echo.
echo 依赖安装完成，可运行 启动分析器.bat 启动程序。
pause
