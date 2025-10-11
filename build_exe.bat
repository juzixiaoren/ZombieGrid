@echo off
REM 在项目根运行此脚本（cmd.exe），会创建 .venv、安装 requirements 并用 pyinstaller 打包
set ENTRY_SCRIPT=app.py
set APP_NAME=ZombieGridTool

REM 建立虚拟环境并激活
python -m venv .venv
call .venv\Scripts\activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

REM 验证关键依赖是否可导入
python - <<EOF
import sys
try:
    import sqlalchemy, pandas, numpy, scipy
    print("IMPORT_OK", sqlalchemy.__version__)
    sys.exit(0)
except Exception as e:
    print("IMPORT_FAIL", e)
    sys.exit(1)
EOF
if errorlevel 1 (
  echo 依赖导入失败，请检查 requirements.txt 并手动安装缺失包
  pause
  exit /b 1
)

REM 打包：如遇 ModuleNotFoundError，可在下面命令中加入 --hidden-import=sqlalchemy 等
pyinstaller --noconfirm --onefile --name %APP_NAME% --add-data "data;data" "%ENTRY_SCRIPT%"

echo 打包完成，请检查 dist\%APP_NAME%.exe
pause