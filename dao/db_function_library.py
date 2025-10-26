
from sqlalchemy import create_engine
from dao import config
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError
from dao.config import SQLALCHEMY_DATABASE_URI
from sqlalchemy.orm import sessionmaker
from dao.grid_data_structure import IndexData, GridConfig, GridRow, Base, ImportedFiles
from typing import List

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

    def _get_model(self, table_name: str):
        """辅助函数：根据表名获取对应的模型类"""
        table_map = {
            'GridData': IndexData,
            'GridConfig': GridConfig,
            'GridRow': GridRow,
            'ImportedFiles': ImportedFiles
        }
        return table_map.get(table_name)

    def get_record_by_id(self, table_name: str, record_id: int):
        """根据表名和主键ID查询单条记录（ID为主键，因此结果应该只有单个）"""
        model = self._get_model(table_name)
        if not model:
            print(f"未找到表名: {table_name}")
            return None
        # 查询主键
        record = self.session.get(model, record_id) 
        if not record:
            print(f"在表 '{table_name}' 中未找到 ID 为 {record_id} 的记录")
        # 不需要打印找到的记录，由调用者决定
        return record # 返回单个对象或 None
    
    def get_records_by_id(self, table_name: str, record_id: int):
        """根据表名和ID查询记录（本函数备用，适用于根据ID返回多条的情况）"""
        model = self._get_model(table_name)
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
    
    def get_distinct_index_codes(self) -> List[str]:
        """获取 GridData 表中所有唯一的 index_code，以展示给用户"""
        try:
            results = self.session.query(distinct(IndexData.index_code)).order_by(IndexData.index_code).all()
            index_codes = [result[0] for result in results if result[0]]
            return index_codes
        except Exception as e:
            print(f"查询 index_code 时出错: {e}")
            return []
    
    def get_record_by_any(self, table_name: str, **kwargs) -> List:
        """根据表名和任意字段查询记录（返回列表）"""
        model = self._get_model(table_name)
        if not model:
            return []
        records = self.session.query(model).filter_by(**kwargs).all()
        return records

    def get_table_count(self, table_name: str):
        """根据表名统计数据条数"""
        model = self._get_model(table_name)
        if not model:
            print(f"未找到表名: {table_name}")
            return 0
        count = self.session.query(model).count()
        print(f"表 {table_name} 共 {count} 条记录")
        return count

    def get_all_records(self, table_name: str):
        """根据表名获取所有记录,并返回列表"""
        model = self._get_model(table_name)
        if not model:
            return []
        records = self.session.query(model).all()
        return records
    
    def get_all_imported_files(self) -> List[ImportedFiles]:
        """获取所有 ImportedFiles 记录"""
        records = self.session.query(ImportedFiles).all()
        return records
    
    def delete_import_batch(self, import_id: int) -> bool:
        """根据 import_id 删除 ImportedFiles 记录及关联的 GridData 记录"""
        if not import_id:
            print("错误：import_id 无效")
            return False
        
        imported_file_record = self.get_record_by_id('ImportedFiles', import_id)
        if not imported_file_record:
            # get_record_by_id 内部会打印未找到
            return False

        try:
            print(f"正在删除 Import ID: {import_id} (文件: {imported_file_record.file_name or 'N/A'}, Index: {imported_file_record.index_code}) 的数据...")

            # 直接删除 ImportedFiles 记录，依赖外键的 ON DELETE CASCADE 自动删除 GridData
            self.session.delete(imported_file_record)
            self.session.commit()
            print("删除成功。")
            return True
        except Exception as e:
            self.session.rollback()
            print(f"删除 Import ID {import_id} 的数据时出错: {e}")
            return False
    
    
