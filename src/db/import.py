import pandas as pd
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from db.config import SQLALCHEMY_DATABASE_URI

# 导入您定义的数据结构
from db.grid_data_structure import IndexData, Base

json_file_path="DataBase/DataFolder/399971perf.json"

class DataImporter:
    """
    数据导入器 - 将指数数据导入到您定义的GridData表中
    """
    
    def __init__(self,SQLALCHEMY_DATABASE_URI):
        """
        初始化数据导入器
        :param database_url: 数据库连接URL
        """
        self.engine = create_engine(SQLALCHEMY_DATABASE_URI)

        # 使用您在GridDataStructure.py中定义的表结构
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()
    
    def import_from_json(self, json_file_path):
        """
        直接从JSON文件导入数据到GridData表
        :param json_file_path: JSON文件路径
        """
        try:
            # 读取JSON文件
            with open(json_file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
            
            records = []
            # 处理JSON数据
            for item in data:
                # # 处理日期字段
                # date_str = item.get('日期Date')
                # if isinstance(date_str, str):
                #     date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00')) if 'T' in date_str else datetime.strptime(date_str, '%Y-%m-%d')
                # else:
                #     date_obj = date_str
                
                index_data = IndexData(
                    date=item.get('日期Date'),
                    index_code=item.get('指数代码Index Code'),
                    index_chinese_full_name=item.get('指数中文全称Index Chinese Name(Full)'),
                    index_chinese_short_name=item.get('指数中文简称Index Chinese Name'),
                    index_english_full_name=item.get('指数英文全称Index English Name(Full)'),
                    index_english_short_name=item.get('指数英文简称Index English Name'),
                    open_price=float(item.get('开盘Open') or 0),
                    high_price=float( item.get('最高High') or 0),
                    low_price=float(item.get('最低Low') or 0),
                    close_price=float(item.get('收盘Close') or 0),
                    change=float( item.get('涨跌Change') or 0),
                    change_percent=float(item.get('涨跌幅(%)Change(%)') or 0),
                    volume_m_shares=float(  item.get('成交量（万手）Volume(M Shares)') or 0),
                    turnover=float(item.get('成交金额（亿元）Turnover') or 0),
                    cons_number=int(item.get('样本数量ConsNumber') or 0)
                )
                records.append(index_data)
            
            # 批量插入数据
            self.session.add_all(records)
            self.session.commit()
            print(f"成功从JSON文件导入 {len(records)} 条记录到GridData表")
            return True
            
        except Exception as e:
            self.session.rollback()
            print(f"从JSON文件导入数据时出错: {e}")
            return False
    
    # def import_from_json_array(self, json_array):
    #     """
    #     从JSON数组导入数据到GridData表
    #     :param json_array: JSON数据数组
    #     """
    #     try:
    #         records = []
    #         for item in json_array:
    #             # 处理日期字段
    #             date_str = item.get('日期Date')
    #             if isinstance(date_str, str):
    #                 date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00')) if 'T' in date_str else datetime.strptime(date_str, '%Y-%m-%d')
    #             else:
    #                 date_obj = date_str
                
    #             index_data = IndexData(
    #                   date=date_obj,
    #                 index_code=item.get('指数代码Index Code'),
    #                 index_chinese_full_name=item.get('指数中文全称Index Chinese Name(Full)'),
    #                 index_chinese_short_name=item.get('指数中文简称Index Chinese Name'),
    #                 index_english_full_name=item.get('指数英文全称Index English Name(Full)'),
    #                 index_english_short_name=item.get('指数英文简称Index English Name'),
    #                 open_price=float(item.get('开盘Open') or 0),
    #                 high_price=float( item.get('最高High') or 0),
    #                 low_price=float(item.get('最低Low') or 0),
    #                 close_price=float(item.get('收盘Close') or 0),
    #                 change=float( item.get('涨跌Change') or 0),
    #                 change_percent=float(item.get('涨跌幅(%)Change(%)') or 0),
    #                 volume_m_shares=float(  item.get('成交量（万手）Volume(M Shares)') or 0),
    #                 turnover=float(item.get('成交金额（亿元）Turnover') or 0),
    #                 cons_number=int(item.get('样本数量ConsNumber') or 0)
    #             )
    #             records.append(index_data)
            
    #         self.session.add_all(records)
    #         self.session.commit()
    #         print(f"成功从JSON数组导入 {len(records)} 条记录到GridData表")
    #         return True
            
    #     except Exception as e:
    #         self.session.rollback()
    #         print(f"从JSON数组导入数据时出错: {e}")
    #         return False
    
    def close(self):
        """
        关闭数据库会话
        """
        self.session.close()

# 使用示例
if __name__ == "__main__":
    # 创建导入器实例
    importer = DataImporter(SQLALCHEMY_DATABASE_URI)
    
    # 从JSON文件导入数据
    importer.import_from_json(json_file_path)
    
    # 关闭连接
    importer.close()