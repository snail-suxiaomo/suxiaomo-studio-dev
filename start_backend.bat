@echo off
chcp 65001 >nul
title suxiaomo-backend (9100)
cd /d "%~dp0backend"

REM 先清理占用 9100 端口的旧后端进程（只杀端口持有者，不误伤其他 python）
echo [suxiaomo] 检查并清理 9100 端口旧进程...
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr /i ":9100" ^| findstr /i "LISTENING"') do (
    if not "%%a"=="" (
        echo [suxiaomo] 终止旧进程 PID=%%a
        taskkill /F /PID %%a >nul 2>&1
    )
)
ping -n 2 127.0.0.1 >nul 2>&1

echo [suxiaomo] 启动后端: uvicorn app:app --host 127.0.0.1 --port 9100
echo [suxiaomo] 接口地址 http://127.0.0.1:9100  (Ctrl+C 或关闭本窗口即停止)
echo.
venv\Scripts\uvicorn.exe app:app --host 127.0.0.1 --port 9100
