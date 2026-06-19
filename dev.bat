@echo off
chcp 65001 >nul
cd /d "%~dp0flypig"
echo ┌─────────────────────────────────────┐
echo │   FlyPig 开发模式                     │
echo │   后端: uvicorn + reload :8321       │
echo │   前端: 另开终端 npx vite --host     │
echo └─────────────────────────────────────┘
echo.
python -m uvicorn asgi:app --reload --host 127.0.0.1 --port 8321
pause
