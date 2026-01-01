import pandas as pd
import json
from datetime import datetime
import os


def excel_to_json(excel_file_path, json_file_path):
    """
    将Excel文件转换为JSON格式
    :param excel_file_path: Excel文件路径
    :param json_file_path: 输出JSON文件路径
    """
    try:
        # 读取Excel文件
        print(f"正在读取Excel文件: {excel_file_path}")
        df = pd.read_excel(excel_file_path)
        
        # 处理日期列，确保日期格式正确
        date_columns = ['Date', 'date']
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        # 将DataFrame转换为字典列表
        records = df.to_dict('records')
        
        # 处理日期格式化
        for record in records:
            for key, value in record.items():
                if isinstance(value, pd.Timestamp):
                    # 将pandas Timestamp转换为ISO格式字符串
                    record[key] = value.isoformat() if pd.notna(value) else None
                elif pd.isna(value):
                    # 将NaN值转换为None
                    record[key] = None
        
        # 保存为JSON文件
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        
        print(f"成功转换 {len(records)} 条记录")
        print(f"JSON文件已保存至: {json_file_path}")
        return True
        
    except Exception as e:
        print(f"转换过程中出错: {e}")
        return False

def validate_json(json_file_path):
    """
    验证生成的JSON文件是否有效
    :param json_file_path: JSON文件路径
    """
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"JSON文件验证成功，包含 {len(data)} 条记录")
        return True
    except Exception as e:
        print(f"JSON文件验证失败: {e}")
        return False

if __name__ == "__main__":
    # 配置文件路径
    excel_file = "./data/database_folder/399971perf.xlsx"  # 输入的Excel文件
    json_file = "./data/database_folder/399971perf.json"   # 输出的JSON文件

    # 检查输入文件是否存在
    if not os.path.exists(excel_file):
        print(f"错误: 找不到Excel文件 {excel_file}")
        print("请确保Excel文件存在于当前目录，或修改excel_file变量指定正确路径")
        exit(1)
    
    # 执行转换
    print("开始Excel到JSON转换...")
    success = excel_to_json(excel_file, json_file)
    
    if success:
        # 验证生成的JSON文件
        validate_json(json_file)
        print("转换完成!")
    else:
        print("转换失败!")
        exit(1)