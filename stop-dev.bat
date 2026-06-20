@echo off
chcp 65001 >nul
echo ┌──────────────────────────────────────────┐
echo │   FlyPig — 停止全部开发服务               │
echo │   后端:8321 / 前端:5173 / 文档:8765       │
echo └──────────────────────────────────────────┘
echo.

for %%p in (8321 5173 8765) do (
    for /f "tokens=5" %%a in ('netstat -aon ^| find ":%%p" ^| find "LISTENING"') do (
        taskkill /f /pid %%a >nul 2>&1 && echo    √ 端口 %%p 已释放
    )
)

echo.
echo √ 所有服务已停止
echo.
pause
