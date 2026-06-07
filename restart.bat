@echo off
echo ┌──────────────────────────────┐
echo │   FlyPig — 重启服务器        │
echo └──────────────────────────────┘
echo.

echo [1/2] 停止旧服务器...
python -m flypig --kill-port 8321
echo.

echo [2/2] 启动新服务器...
start "" python -m flypig --web
echo.
echo √ 服务器正在启动...
echo 访问 http://127.0.0.1:8321
echo.

pause
