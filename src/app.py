from db import config, grid_data_structure,db_function_library
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
import pymysql
if __name__ == "__main__":
    print("网格交易神器")
    engine = create_engine(config.SQLALCHEMY_DATABASE_URI)
    try:
        with engine.connect() as connection:
            print("数据库连接成功")
            # 自动创建表
    except OperationalError:
        print("注意！创建数据库的账号和密码需要在config文件中进行修改")
        print("数据库连接失败，是否自动创建数据库(y/n)")
        try:
            if(input() == 'y'or'Y'):
                db_function_library.create_database_if_not_exists()
            else:
                print("数据库未创建，即将退出")
        except:
            print("数据库创建失败")