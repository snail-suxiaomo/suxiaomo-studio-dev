@echo off
chcp 65001 >nul
setlocal
set ROOT=%~dp0
title suxiaomo-studio 启动器

echo ============================================================
echo   suxiaomo-studio 一键启动
echo   后端  -^> http://127.0.0.1:9100  (新窗口: suxiaomo-backend)
echo   前端  -^> http://127.0.0.1:5173  (新窗口: suxiaomo-frontend)
echo ============================================================
echo.

start "suxiaomo-backend" cmd /k "%ROOT%start_backend.bat"
start "suxiaomo-frontend" cmd /k "%ROOT%start_frontend.bat"

echo 已分别在新窗口启动后端与前端。
echo 浏览器打开 http://127.0.0.1:5173 即可使用。
echo （后端启动时会自动清理 9100 端口旧进程；前端 5173 若被占用请关闭同名窗口）
echo.
pause
