@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 启动 FlyPig WSL 开发模式...
echo 首次使用请先运行: wsl bash scripts/setup-wsl.sh
echo.
wsl bash scripts/dev-wsl.sh
pause
