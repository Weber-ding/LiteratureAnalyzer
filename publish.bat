@echo off
chcp 65001 >nul 2>&1
title 版本迭代 - 提交并推送到 GitHub
setlocal

set GIT=C:\Users\15307\Tools\git\bin\git.exe
set GH=C:\Users\15307\Tools\gh\bin\gh.exe

if not exist "%GIT%" (
    echo [错误] 未找到 git，请先安装 Git。
    pause
    exit /b 1
)

set PATH=C:\Users\15307\Tools\git\bin;C:\Users\15307\Tools\gh\bin;%PATH%

cd /d "%~dp0"

echo === 当前状态 ===
"%GIT%" status -sb
echo.

set /p MSG="请输入本次更新说明（留空则使用默认）: "
if "%MSG%"=="" set MSG=更新

echo.
echo === 暂存变更 ===
"%GIT%" add -A

echo.
echo === 提交 ===
"%GIT%" commit -m "%MSG%"
if errorlevel 1 (
    echo [提示] 没有可提交的变更。
    pause
    exit /b 0
)

echo.
echo === 推送到 GitHub ===
"%GIT%" push origin main
if errorlevel 1 (
    echo [错误] 推送失败，请检查网络或权限。
    pause
    exit /b 1
)

echo.
echo === 成功 ===
echo 已提交并推送到 GitHub。
pause
