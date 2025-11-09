# dao/config.py
import os
import sys

# --- 新的 PyInstaller 路径逻辑 ---

if getattr(sys, 'frozen', False):
    # 如果是打包后的 .exe 运行 (sys.frozen == True)
    # base_dir 就是 .exe 文件所在的目录
    base_dir = os.path.dirname(sys.executable)
else:
    # 如果是作为 .py 脚本运行
    # base_dir 就是项目根目录 (ZombieGrid/)
    # (os.path.abspath(__file__) 是 .../ZombieGrid/dao/config.py)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 构建数据库文件的绝对路径
db_path = os.path.join(base_dir, "data", "zombiegrid.db")

# 转换为 SQLAlchemy URI (Windows 绝对路径需要三个斜杠 ///)
# os.path.abspath 确保路径在 Windows 上是反斜杠，但 f-string 能处理
SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.abspath(db_path)}"

# --- 修复结束 ---

SQLALCHEMY_TRACK_MODIFICATIONS = False

# (可选) 调试时可以取消注释下面这行，查看 .exe 运行时打印的路径
# print(f"DEBUG: Database URI set to: {SQLALCHEMY_DATABASE_URI}")
# import time
# time.sleep(5)