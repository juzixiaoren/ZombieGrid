import os
import pandas as pd
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .config import SQLALCHEMY_DATABASE_URI
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
from .grid_data_structure import IndexData, Base,GridConfig,GridRow

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
    def import_market_data_from_json(self, json_file_path):
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
        
    def import_grid_model(self, result: dict) -> bool:  
        try:
            # Step 1: 创建 GridConfig 实例
            config_data = result["config"]
            grid_config = GridConfig(
            name=config_data.get("name"),
            a=config_data["a"],
            b=config_data["b"],
            first_trigger_price=config_data["first_trigger_price"],
            total_rows=config_data["total_rows"],
            buy_amount=config_data["buy_amount"]
        )

            # Step 2: 创建 GridRow 实例列表
            grid_rows = []
            for row_data in result["rows"]:
                row = GridRow(
                fall_percent=row_data["fall_percent"],
                level_ratio=row_data["level_ratio"],
                buy_trigger_price=row_data["buy_trigger_price"],
                buy_price=row_data["buy_price"],
                buy_amount=row_data["buy_amount"],
                shares=row_data["shares"],
                sell_trigger_price=row_data["sell_trigger_price"],
                sell_price=row_data["sell_price"],
                yield_rate=row_data["yield_rate"],
                profit_amount=row_data["profit_amount"]
            )
                grid_rows.append(row)

            # Step 3: 关联并保存
            grid_config.rows = grid_rows
            self.session.add(grid_config)
            self.session.commit()

            print(f"网格配置已保存, ID: {grid_config.id}，共 {len(grid_config.rows)} 行")
            return True

        except Exception as e:
            self.session.rollback()
            print(f"导入网格模型时出错: {e}")
            return False
   
    def close(self):
        """
        关闭数据库会话
        """
        self.session.close()






# 使用示例
if __name__ == "__main__":
    # 创建导入器实例
    importer = DataImporter(SQLALCHEMY_DATABASE_URI)
    
    # # 从JSON文件导入数据
    json_file_path = os.path.join(BASE_DIR, "database_folder", "399971perf.json")
    importer.import_market_data_from_json(json_file_path)
    
    

    # 关闭连接
    importer.close()