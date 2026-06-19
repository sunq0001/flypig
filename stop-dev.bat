@echo off
chcp 65001 >nul
echo ┌─────────────────────────────────────┐
echo │   FlyPig — 停止开发服务              │
echo └─────────────────────────────────────┘
echo.

echo [1/2] 停止后端（8321端口）...
for /f "tokens=5" %%a in ('netstat -aon ^| find ":8321" ^| find "LISTENING"') do (
    taskkill /f /pid %%a >nul 2>&1
    echo    √ 端口 8321 已释放
)

echo [2/2] 停止前端（5173端口）...
for /f "tokens=5" %%a in ('netstat -aon ^| find ":5173" ^| find "LISTENING"') do (
    taskkill /f /pid %%a >nul 2>&1
    echo    √ 端口 5173 已释放
)

echo.
echo √ 所有服务已停止
echo.
pause
