@echo off
chcp 65001 >nul 2>&1
title 打包文献智能分析器
setlocal

set VENV=%~dp0.venv
set PYINSTALLER=%VENV%\Scripts\pyinstaller.exe

if not exist "%PYINSTALLER%" (
    echo [错误] 未找到 PyInstaller，请先运行 install_deps.bat 安装依赖。
    pause
    exit /b 1
)

echo.
echo === 开始打包 ===
echo.

"%PYINSTALLER%" ^
  --onedir ^
  --windowed ^
  --name "LiteratureAnalyzer" ^
  --hidden-import fitz ^
  --hidden-import pptx ^
  --hidden-import docx ^
  --clean ^
  --noconfirm ^
  "%~dp0main.py"

if errorlevel 1 (
    echo.
    echo [错误] 打包失败，请检查上方日志。
    pause
    exit /b 1
)

echo.
echo === 复制配置文件到输出目录 ===
copy /Y "%~dp0config.json" "%~dp0dist\LiteratureAnalyzer\config.json" >nul
copy /Y "%~dp0keyword_map.json" "%~dp0dist\LiteratureAnalyzer\keyword_map.json" >nul

echo.
echo === 打包完成 ===
echo 输出目录: %~dp0dist\LiteratureAnalyzer\
echo 主程序: LiteratureAnalyzer.exe
echo 配置文件 config.json 和 keyword_map.json 已复制到输出目录，可直接编辑。
echo.
pause
