import os
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .config import SQLALCHEMY_DATABASE_URI
from datetime import datetime
# 引入新的统一加载器
from .market_data_loader import load_market_data

from .grid_data_structure import IndexData, Base, GridConfig, GridRow, ImportedFiles

class DataImporter:
    def __init__(self, SQLALCHEMY_DATABASE_URI):
        self.engine = create_engine(SQLALCHEMY_DATABASE_URI)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()

    def import_market_data(self, file_path, source_type):
        """
        统一入口：导入行情数据并适配数据库结构
        参数:
            file_path: 文件绝对路径
            source_type: 数据源类型字符串 (如 'wind', 'ishare_excel')
        """
        try:
            # 1. 调用 DAO 加载器，传入用户指定的 source_type
            df, detected_code = load_market_data(file_path, source_type)
            
            if df.empty:
                print("❌ 加载的数据为空")
                return False

            # --- 核心适配步骤：补充数据库必需的计算字段 ---
            
            # 1.1 计算涨跌 (Change) 和 涨跌幅 (ChangePercent)
            # 涨跌 = 今天收盘 - 昨天收盘
            df['Change'] = df['Close'].diff()
            # 涨跌幅 = (今天收盘 - 昨天收盘) / 昨天收盘 * 100
            df['ChangePercent'] = df['Close'].pct_change() * 100
            
            # 第一行数据因为没有前一天，diff会产生NaN，我们将其填充为 0
            df['Change'] = df['Change'].fillna(0.0)
            df['ChangePercent'] = df['ChangePercent'].fillna(0.0)

            # --- 结束适配 ---

            file_name = os.path.basename(file_path)
            
            # 2. 创建 ImportedFiles 记录
            min_date = df['Date'].min()
            max_date = df['Date'].max()
            
            imported_file = ImportedFiles(
                file_name=file_name,
                index_code=detected_code,
                import_time=datetime.utcnow(),
                record_count=len(df),
                date_range=f"{min_date.strftime('%Y-%m-%d')} ~ {max_date.strftime('%Y-%m-%d')}"
            )
            self.session.add(imported_file)
            self.session.flush() # 刷新以获取 ID

            # 3. 批量转换为 IndexData 对象 (ORM)
            records = []
            for _, row in df.iterrows():
                idx_data = IndexData(
                    import_id=imported_file.id,
                    date=row['Date'].date(),
                    index_code=detected_code,
                    
                    # 数据库必需的名称字段，因为新数据没有，全部用 Code 填充
                    index_chinese_full_name=detected_code,
                    index_chinese_short_name=detected_code,
                    index_english_full_name=detected_code,
                    
                    # 基础数据
                    open_price=row['Open'],
                    high_price=row['High'],
                    low_price=row['Low'],
                    close_price=row['Close'],
                    
                    # 计算出的数据
                    change=row['Change'],
                    change_percent=row['ChangePercent'],
                    
                    # 单位注意：原有数据库可能是"万手"，这里直接存"手"或"个"
                    volume_m_shares=row['Volume'], 
                    
                    # 缺失的业务字段，填充 0
                    turnover=0.0,
                    cons_number=0
                )
                records.append(idx_data)

            self.session.add_all(records)
            self.session.commit()
            print(f"✅ 成功导入 {len(records)} 条记录 (Import ID: {imported_file.id})")
            print(f"   已自动计算涨跌幅，并填充缺失字段。")
            return True

        except Exception as e:
            self.session.rollback()
            print(f"❌ 导入失败: {e}")
            # import traceback
            # traceback.print_exc()
            return False

    def import_grid_model(self, result: dict) -> bool:
        """保存策略配置（保持不变）"""
        try:
            config_data = result["config"]
            grid_config = GridConfig(
                name=config_data.get("name"),
                a=config_data["a"],
                b=config_data["b"],
                first_trigger_price=config_data["first_trigger_price"],
                total_rows=config_data["total_rows"],
                buy_amount=config_data["buy_amount"]
            )
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
        self.session.close()