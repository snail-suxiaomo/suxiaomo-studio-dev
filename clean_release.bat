@echo off
chcp 65001 >nul
title 清理 suxiaomo-studio-release 残留（解锁 win-unpacked）
echo ================================================
echo  清理 suxiaomo-studio-release 打包残留目录
echo  会结束 node / electron / python / uvicorn 进程
echo ================================================
echo.
echo [1/2] 结束可能锁住文件的进程...
taskkill /F /IM node.exe 2>nul
taskkill /F /IM electron.exe 2>nul
taskkill /F /IM python.exe 2>nul
taskkill /F /IM uvicorn.exe 2>nul
taskkill /F /IM suxiaomo-studio.exe 2>nul
echo 等待进程释放文件锁...
timeout /t 3 >nul

echo.
echo [2/2] 删除 suxiaomo-studio-release 下的残留目录...
rmdir /s /q "F:\suxiaomo-studio-release\win-unpacked" 2>nul
rmdir /s /q "F:\suxiaomo-studio-release\suxiaomo-studio-v1.0.0" 2>nul
rmdir /s /q "F:\suxiaomo-studio-release\.old-win-unpacked" 2>nul
echo.
echo 完成！现在可以双击 build.bat 重新打包。
echo（如果上面仍提示删不掉，请手动关闭所有 suxiaomo-studio 窗口再试）
echo.
pause
