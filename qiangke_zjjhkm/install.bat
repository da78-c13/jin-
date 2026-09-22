@echo off
chcp 65001 >nul

echo =====================================================
echo    📦  抢课工具 - 一键安装依赖
echo =====================================================
echo.

python install_deps.py

if %errorlevel% neq 0 (
    echo.
    echo   未找到 Python，请先安装 Python 3.8+
    echo   下载地址: https://www.python.org/downloads/
    echo.
    pause
)