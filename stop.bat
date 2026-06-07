@echo off
echo ┌──────────────────────────────┐
echo │     FlyPig — 停止服务器       │
echo └──────────────────────────────┘
echo.

python -m flypig --kill-port 8321

if %ERRORLEVEL% EQU 0 (
    echo.
    echo √ 服务器已停止
) else (
    echo.
    echo ! 停止失败，请尝试手动关闭
)

pause
