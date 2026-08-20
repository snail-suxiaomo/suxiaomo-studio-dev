@echo off
chcp 65001 >nul
title suxiaomo-frontend (5173)
cd /d "%~dp0frontend"
echo [suxiaomo] 启动前端: npm run dev (vite, 端口 5173)
echo [suxiaomo] 浏览器访问 http://127.0.0.1:5173  (Ctrl+C 或关闭本窗口即停止)
echo.
call npm run dev
