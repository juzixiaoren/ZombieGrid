@echo off
setlocal enabledelayedexpansion

set ENTRY_SCRIPT=app.py
set APP_NAME=ZombieGridTool

REM -----------------------------------------------------------------
REM 确保 Conda 环境已激活 (e.g., conda activate ZombieGrid_venv)
REM -----------------------------------------------------------------
echo Using current activated environment to build...
echo.

REM 检查依赖 (使用你干净的 requirements.txt)
echo Checking dependencies...
pip install -r requirements.txt
IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Failed to install dependencies from requirements.txt.
    pause
    exit /b 1
)

echo Dependencies OK.
echo Starting PyInstaller build...
echo This may take a few minutes...

REM --- 修改：移除了 --add-data "data;data" ---
pyinstaller --noconfirm --onefile --name %APP_NAME% --hidden-import=sqlalchemy --hidden-import=pandas --hidden-import=numpy --hidden-import=scipy --hidden-import=openpyxl --hidden-import=tabulate --hidden-import=alembic "%ENTRY_SCRIPT%"

IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: PyInstaller failed to build.
    pause
    exit /b 1
)

echo.
echo PyInstaller build complete.
echo.

REM --- 新增：将 data 文件夹复制到 dist 目录 ---
echo Copying 'data' folder to dist directory...
REM /E 复制子目录(包括空的), /I 如果目标不存在则创建目录, /Y 覆盖同名文件
xcopy /E /I /Y "data" "dist\data\"

IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Failed to copy 'data' folder.
    pause
    exit /b 1
)
REM --- 新增结束 ---


echo -------------------------------------------------
echo Build process finished!
echo Your files are in the 'dist' folder:
echo   - dist\%APP_NAME%.exe
echo   - dist\data\ (External data folder)
echo -------------------------------------------------
pause