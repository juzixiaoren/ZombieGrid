
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from db.grid_data_structure import IndexData,grid_config
from db.config import SQLALCHEMY_DATABASE_URI
from db import config
import json
import pymysql

def export_data_by_id_range(session, start_id=1, end_id=-1, output_json_path=None):
    """
    根据ID范围导出数据（按日期排序后的行号）
    :param session: 数据库会话对象
    :param start_id: 起始ID（从1开始），默认为1
    :param end_id: 结束ID，-1表示导出到最后一行，默认为-1
    :param output_json_path: 输出JSON文件路径（可选）
    :return: 导出的数据列表
    """
    try:
        # 查询所有数据并按日期排序
        query = session.query(IndexData).order_by(IndexData.date)
        all_data = query.all()
        
        # 检查总记录数
        total_records = len(all_data)
        if total_records == 0:
            print("数据库中没有数据")
            return []
        
        # 验证起始ID
        if start_id < 1 or start_id > total_records:
            print(f"错误: 起始ID {start_id} 无效。有效范围为 1 到 {total_records}")
            return []
        
        # 处理结束ID为-1的情况（导出到最后一行）
        if end_id == -1:
            end_id = total_records
        elif end_id > total_records:
            print(f"警告: 结束ID {end_id} 超出范围，将导出到最后一行")
            end_id = total_records
        elif end_id < start_id:
            print(f"错误: 结束ID {end_id} 小于起始ID {start_id}")
            return []
        
        # 提取指定范围的数据（注意：数据库索引从0开始，所以需要减1）
        selected_data = all_data[start_id-1:end_id]
        
        # 转换为字典列表
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
        
        # 如果指定了输出路径，则保存到JSON文件
        if output_json_path:
            with open(output_json_path, 'w', encoding='utf-8') as f:
                json.dump(records, f, ensure_ascii=False, indent=2)
            print(f"成功导出 {len(records)} 条记录到 {output_json_path}")
        
        print(f"成功导出ID范围 {start_id}-{end_id} 的数据，共 {len(records)} 条记录")
        return records
        
    except Exception as e:
        print(f"导出数据时出错: {e}")
        return []


if __name__ == "__main__":
    # 创建数据库引擎和会话
    engine = create_engine(SQLALCHEMY_DATABASE_URI)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # 导出数据示例
        records = export_data_by_id_range(session, 1, 10, "DataBase/DataFolder/test.json")
        
    finally:
        # 关闭会话
        session.close()