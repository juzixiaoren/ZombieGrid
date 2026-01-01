import os
import pandas as pd
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .config import SQLALCHEMY_DATABASE_URI
from datetime import datetime
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
from .grid_data_structure import IndexData, Base,GridConfig,GridRow, ImportedFiles

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
    def import_market_data_from_json(self, json_file_path, file_name=None):
        """
        直接从JSON文件导入数据到GridData表
        导入时应先在ImportedFiles表中创建本次导入的记录，然后将import_id关联到GridData表中
        :param json_file_path: JSON文件路径
        """
        imported_file_record = None

        try:
            # 读取JSON文件，创建导入记录
            with open(json_file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)

            if not data:
                print("JSON文件为空或格式不正确")
                return False
            
            records = []
            min_date, max_date = None, None
            first_record = data[0]
            index_code_from_data = first_record.get('指数代码Index Code') # index_code 是xlsx里写的指数代码
            
            
            imported_file_record = ImportedFiles(
                file_name=file_name,
                index_code = index_code_from_data,
                import_time=datetime.utcnow(),
                record_count=len(data)
            )
            self.session.add(imported_file_record)
            self.session.flush()  # 获取自动生成的ID
            new_import_id = imported_file_record.id

            # 准备GridData记录并关联import_id

            for item in data:
                # --- 开始修改 ---
                # 1. 获取日期整数
                date_int = item.get('日期Date')

                # 2. 将整数转换为datetime对象，再提取date部分
                date_obj = datetime.strptime(str(date_int), '%Y%m%d').date()

                if min_date is None or date_obj < min_date:
                    min_date = date_obj
                if max_date is None or date_obj > max_date:
                    max_date = date_obj

                

                index_data = IndexData(
                    import_id=new_import_id,
                    date=date_obj, # <--- 使用转换后的日期对象
                    # --- 结束修改 ---
                    index_code=item.get('指数代码Index Code') if item.get('指数代码Index Code') is not None else "Unknown",
                    index_chinese_full_name=item.get('指数中文全称Index Chinese Name(Full)'),
                    index_chinese_short_name=item.get('指数中文简称Index Chinese Name'),
                    index_english_full_name=item.get('指数英文全称Index English Name(Full)'),
                    # index_english_short_name=item.get('指数英文简称Index English Name'),
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

            # 更新导入记录的日期范围
            if min_date and max_date:
                imported_file_record.date_range = f"{min_date.strftime('%Y-%m-%d')} ~ {max_date.strftime('%Y-%m-%d')}"
                self.session.commit()  # 提交以保存导入记录的更新
            
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
    json_file_path = "data/database_folder/399971perf.json"
    importer.import_market_data_from_json(json_file_path)
    
    

    # 关闭连接
    importer.close()