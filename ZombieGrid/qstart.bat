@echo off
setlocal enabledelayedexpansion

REM 检查conda是否安装
where conda >nul 2>nul
if %errorlevel% neq 0 (
    echo Conda is not installed or not in PATH.
    pause
    exit /b 1
)

REM 激活conda环境
echo Activating conda environment 'ZombieGrid_venv'...
call conda activate ZombieGrid_venv
if %errorlevel% neq 0 (
    echo Failed to activate conda environment 'ZombieGrid_venv'.
    echo Creating new environment...
    call conda create -n ZombieGrid_venv python=3.13 -y
    call conda activate ZombieGrid_venv
)


REM 强制清理可能残留的进程
taskkill /F /IM node.exe /FI "WINDOWTITLE eq Frontend*" >nul 2>nul
taskkill /F /IM python.exe /FI "WINDOWTITLE eq Backend*" >nul 2>nul

REM 在新窗口运行主程序
start "" python app.py

call conda deactivate
echo Environment deactivated.
pause

