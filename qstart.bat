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

REM 安装Python依赖
if exist requirements.txt (
    echo Installing Python dependencies from requirements.txt...
    
    REM 升级pip
    python -m pip install --upgrade pip
    
    REM 直接使用requirements.txt安装所有依赖
    pip install -r requirements.txt
    
    REM 验证关键包是否安装成功
    echo Verifying key installations...
    python -c "import torch; print('✓ PyTorch installed, CUDA available:', torch.cuda.is_available())" 2>nul
    if %errorlevel% neq 0 (
        echo ⚠ PyTorch not found, installing CUDA version...
        pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
    )
    
    python -c "import faiss; print('✓ FAISS installed')" 2>nul
    if %errorlevel% neq 0 (
        echo ⚠ FAISS not found, installing GPU version...
        pip install faiss-gpu
    )
    
    python -c "import PyPDF2; print('✓ PyPDF2 installed')" 2>nul
    if %errorlevel% neq 0 (
        echo ✗ PyPDF2 installation failed
        pause
        exit /b 1
    )
    
    echo ✓ All dependencies installed successfully!
) else (
    echo ✗ server\requirements.txt not found!
    pause
    exit /b 1
)

REM 强制清理可能残留的进程
taskkill /F /IM node.exe /FI "WINDOWTITLE eq Frontend*" >nul 2>nul
taskkill /F /IM python.exe /FI "WINDOWTITLE eq Backend*" >nul 2>nul

call conda deactivate
echo Environment deactivated.
pause
