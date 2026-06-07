@echo off
echo ┌──────────────────────────────┐
echo │     FlyPig — 启动服务器       │
echo └──────────────────────────────┘
echo.

start "" python -m flypig --web
echo.
echo √ 服务器正在启动...
echo 访问 http://127.0.0.1:8321
echo.

pause
