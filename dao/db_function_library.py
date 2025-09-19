
from sqlalchemy import create_engine
from dao import config
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError
from dao.config import SQLALCHEMY_DATABASE_URI
from sqlalchemy.orm import sessionmaker
from dao.grid_data_structure import IndexData, GridConfig, GridRow, Base

def init_db():
    engine = create_engine(config.SQLALCHEMY_DATABASE_URI)
    try:
        with engine.connect() as connection:
            print("数据库连接成功")
    except OperationalError:
        print("数据库连接失败，请检查配置(在config.py中,检查MySQL的用户名，密码，端口，数据库名等)")
        return None
class DBSessionManager:
    def __init__(self):
        self.engine = create_engine(SQLALCHEMY_DATABASE_URI)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.session = self.SessionLocal()

    def __enter__(self):
        self.session = self.SessionLocal()
        return self.session

    def __exit__(self, exc_type, exc_value, traceback):
        self.session.close()

    def get_record_by_id(self, table_name: str, record_id: int):
        """根据表名和ID查询记录（可能多条）"""
        table_map = {
            'GridData': IndexData,
            'GridConfig': GridConfig,
            'GridRow': GridRow
        }
        model = table_map.get(table_name)
        if not model:
            print(f"未找到表名: {table_name}")
            return []
        records = self.session.query(model).filter_by(id=record_id).all()
        if records:
            for record in records:
                print(record)
        else:
            print(f"未找到ID为 {record_id} 的记录")
        return records
    
    def get_record_by_any(self, table_name: str, **kwargs):
        """根据表名和任意字段查询记录（可能多条）"""
        table_map = {
            'GridData': IndexData,
            'GridConfig': GridConfig,
            'GridRow': GridRow
        }
        model = table_map.get(table_name)
        if not model:
            print(f"未找到表名: {table_name}")
            return []
        records = self.session.query(model).filter_by(**kwargs).all()
        if not records:
            print(f"未找到符合条件的记录: {kwargs}")
        return records

    def get_table_count(self, table_name: str):
        """根据表名统计数据条数"""
        table_map = {
            'GridData': IndexData,
            'GridConfig': GridConfig,
            'GridRow': GridRow
        }
        model = table_map.get(table_name)
        if not model:
            print(f"未找到表名: {table_name}")
            return 0
        count = self.session.query(model).count()
        print(f"表 {table_name} 共 {count} 条记录")
        return count

    def get_all_records(self, table_name: str):
        """根据表名获取所有记录,并返回列表"""
        table_map = {
            'GridData': IndexData,
            'GridConfig': GridConfig,
            'GridRow': GridRow
        }
        model = table_map.get(table_name)
        if not model:
            return []
        records = self.session.query(model).all()
        return records