@echo off
chcp 65001 >nul
echo ┌─────────────────────────────────────┐
echo │   FlyPig 开发模式启动                 │
echo │   后端: uvicorn :8321（热加载）       │
echo │   前端: Vite HMR :5173               │
echo └─────────────────────────────────────┘
echo.

echo [1/2] 启动后端（uvicorn --reload）...
start "flypig-backend" cmd /c "cd /d %~dp0flypig && python -m uvicorn asgi:app --reload --host 127.0.0.1 --port 8321"

echo [2/2] 启动前端（Vite HMR）...
start "flypig-frontend" cmd /c "cd /d %~dp0flypig\frontend\static_vite && npx vite --host"

echo.
echo   后端 API:  http://127.0.0.1:8321
echo   前端 UI:   http://localhost:5173
echo   后端热加载：改 .py 文件自动重启
echo   前端热加载：改 .vue/.js 秒级更新
echo.
pause
