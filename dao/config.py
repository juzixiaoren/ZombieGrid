import os

# # MySQL 配置 (已弃用)
# MYSQL_CONFIG = {
#     'host': '127.0.0.1',
#     'user': 'root',            # 修改为你自己的用户名
#     'password': '12345678',  # 修改为你自己的密码
#     'database': 'ZombieGrid'  #修改为你创建的库名称 ，建议还是这个名
# }

# 数据库文件名为 'zombiegrid.db'，并存放在项目根目录
SQLALCHEMY_DATABASE_URI = "sqlite:///data/zombiegrid.db"
SQLALCHEMY_TRACK_MODIFICATIONS = False