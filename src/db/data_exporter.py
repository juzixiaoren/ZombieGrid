import os
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .config import SQLALCHEMY_DATABASE_URI
from .grid_data_structure import IndexData, Base

class DataExporter:
    """
    数据导出器 - 导出数据库中的数据到 JSON 文件等
    """
    def __init__(self, SQLALCHEMY_DATABASE_URI):
        self.engine = create_engine(SQLALCHEMY_DATABASE_URI)
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()

    def export_data_by_id_range(self, start_id=1, end_id=-1, output_json_path=None):
        """
        根据ID范围导出数据（按日期排序后的行号）
        :param start_id: 起始ID（从1开始），默认为1
        :param end_id: 结束ID，-1表示导出到最后一行，默认为-1
        :param output_json_path: 输出JSON文件路径（可选）
        :return: 导出的数据列表
        """
        try:
            query = self.session.query(IndexData).order_by(IndexData.date)
            all_data = query.all()
            total_records = len(all_data)
            if total_records == 0:
                print("数据库中没有数据")
                return []
            if start_id < 1 or start_id > total_records:
                print(f"错误: 起始ID {start_id} 无效。有效范围为 1 到 {total_records}")
                return []
            if end_id == -1:
                end_id = total_records
            elif end_id > total_records:
                print(f"警告: 结束ID {end_id} 超出范围，将导出到最后一行")
                end_id = total_records
            elif end_id < start_id:
                print(f"错误: 结束ID {end_id} 小于起始ID {start_id}")
                return []
            selected_data = all_data[start_id-1:end_id]
            records = []
            for data in selected_data:
                record = {
                    'date': data.date.isoformat() if hasattr(data.date, 'isoformat') else str(data.date),
                    'index_code': data.index_code,
                    'index_chinese_full_name': data.index_chinese_full_name,
                    'index_chinese_short_name': data.index_chinese_short_name,
                    'index_english_full_name': data.index_english_full_name,
                    'index_english_short_name': data.index_english_short_name,
                    'open_price': float(data.open_price) if data.open_price is not None else 0.0,
                    'high_price': float(data.high_price) if data.high_price is not None else 0.0,
                    'low_price': float(data.low_price) if data.low_price is not None else 0.0,
                    'close_price': float(data.close_price) if data.close_price is not None else 0.0,
                    'change': float(data.change) if data.change is not None else 0.0,
                    'change_percent': float(data.change_percent) if data.change_percent is not None else 0.0,
                    'volume_m_shares': float(data.volume_m_shares) if data.volume_m_shares is not None else 0.0,
                    'turnover': float(data.turnover) if data.turnover is not None else 0.0,
                    'cons_number': int(data.cons_number) if data.cons_number is not None else 0
                }
                records.append(record)
            if output_json_path:
                with open(output_json_path, 'w', encoding='utf-8') as f:
                    json.dump(records, f, ensure_ascii=False, indent=2)
                print(f"成功导出 {len(records)} 条记录到 {output_json_path}")
            print(f"成功导出ID范围 {start_id}-{end_id} 的数据，共 {len(records)} 条记录")
            return records
        except Exception as e:
            print(f"导出数据时出错: {e}")
            return []

    def get_total_records_count(self):
        """
        获取数据库中总记录数
        :return: 记录总数
        """
        try:
            count = self.session.query(IndexData).count()
            return count
        except Exception as e:
            print(f"获取记录总数时出错: {e}")
            return 0

    def print_data_summary(self):
        """
        打印数据摘要信息
        """
        try:
            total_count = self.get_total_records_count()
            earliest_date = self.session.query(IndexData.date).order_by(IndexData.date).first()
            latest_date = self.session.query(IndexData.date).order_by(IndexData.date.desc()).first()
            print(f"=== 数据库摘要 ===")
            print(f"总记录数: {total_count}")
            if earliest_date and earliest_date[0]:
                print(f"最早日期: {earliest_date[0]}")
            if latest_date and latest_date[0]:
                print(f"最新日期: {latest_date[0]}")
            print(f"==================")
        except Exception as e:
            print(f"获取数据摘要时出错: {e}")

    def close(self):
        self.session.close()

# 使用示例
if __name__ == "__main__":
    exporter = DataExporter(SQLALCHEMY_DATABASE_URI)
    exporter.print_data_summary()
    exporter.export_data_by_id_range(1, 10, os.path.join(os.path.dirname(os.path.abspath(__file__)), "database_folder", "output.json"))
    exporter.close()
