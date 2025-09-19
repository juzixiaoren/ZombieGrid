
from sqlalchemy import create_engine
from dao import config
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

def init_db():
    engine = create_engine(config.SQLALCHEMY_DATABASE_URI)
    try:
        with engine.connect() as connection:
            print("数据库连接成功")
    except OperationalError:
        print("数据库连接失败，请检查配置(在config.py中,检查MySQL的用户名，密码，端口，数据库名等)")
        return None
