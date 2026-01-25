import os
import pandas as pd
import numpy as np
import importlib.util

"""
DAO 层组件：统一行情数据加载器 (手动指定版 V2)
修复了 iShares '假 Excel' 报错问题，增加明确的用户引导。
"""

def check_dependency(package_name):
    """检查可选依赖是否安装"""
    spec = importlib.util.find_spec(package_name)
    return spec is not None

def get_excel_engine(file_path):
    """根据扩展名获取推荐引擎"""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.xls':
        if not check_dependency('xlrd'):
             raise ImportError("读取 .xls 文件需要安装 xlrd 库。\n请在终端运行: pip install xlrd>=2.0.1")
        return 'xlrd'
    else:
        return 'openpyxl' # 默认 xlsx

def load_market_data(file_path: str, source_type: str) -> tuple[pd.DataFrame, str]:
    """
    分发入口
    :param source_type: 用户在 CLI 选择的格式类型字符串
    """
    if not os.path.exists(file_path):
        raise ValueError(f"文件不存在: {file_path}")
    
    # 格式路由表
    loaders = {
        'wind': _load_wind_excel,
        'ishare_excel': _load_ishare_excel,
        'csi_excel': _load_csi_excel,
        'nasdaq_csv': _load_nsdaq_csv,
        'bitcoin_tsv': _load_bitcoin_tsv,
    }
    
    if source_type not in loaders:
        raise ValueError(f"未知的格式类型: {source_type}")
        
    loader_func = loaders[source_type]
    
    try:
        return loader_func(file_path)
    except Exception as e:
        # 给用户更友好的错误提示
        raise ValueError(f"解析失败 (格式: {source_type}): {str(e)}")

# --- 各类具体的加载器 ---

def _load_wind_excel(file_path):
    """Wind 导出 Excel 解析器"""
    engine = get_excel_engine(file_path)
    
    # 1. 寻找表头 (包含"日期"和"收盘价")
    df_raw = pd.read_excel(file_path, header=None, nrows=20, engine=engine)
    header_idx = -1
    for i, row in df_raw.iterrows():
        row_str = " ".join([str(v) for v in row.values])
        if "日期" in row_str and "收盘价" in row_str:
            header_idx = i
            break
            
    if header_idx == -1:
         # 尝试英文表头
        for i, row in df_raw.iterrows():
            row_vals = [str(v).lower() for v in row.values]
            if "date" in row_vals and ("close" in row_vals or "收盘价" in row_vals):
                header_idx = i
                break
    
    if header_idx == -1:
        raise ValueError("未找到包含[日期]和[收盘价]的表头行")

    # 2. 读取数据
    df = pd.read_excel(file_path, header=header_idx, engine=engine)
    
    # 3. 映射列 (优先使用后复权)
    col_map = {}
    
    # 策略：先找到 Close 对应的列名
    close_col_name = None
    if "收盘价(后复权)" in df.columns: close_col_name = "收盘价(后复权)"
    elif "收盘价" in df.columns: close_col_name = "收盘价"
    elif "close" in [c.lower() for c in df.columns]: 
        # 找英文 close
        for c in df.columns:
            if c.lower() == 'close': close_col_name = c; break
            
    if close_col_name:
        col_map[close_col_name] = 'Close'
        
    # 映射其他列
    for c in df.columns:
        if c == close_col_name: continue
        c_str = str(c).strip()
        if "日期" in c_str or c_str.lower() == 'date': col_map[c] = 'Date'
        elif c_str in ["开盘价", "开盘", "Open"]: col_map[c] = 'Open'
        elif c_str in ["最高价", "最高", "High"]: col_map[c] = 'High'
        elif c_str in ["最低价", "最低", "Low"]: col_map[c] = 'Low'
        elif "成交量" in c_str or c_str.lower() == 'volume': col_map[c] = 'Volume'

    return _standardize_df(df, col_map, index_code="Wind_Data")

def _load_ishare_excel(file_path):
    """iShares ETF Excel 解析器"""
    engine = get_excel_engine(file_path)
    
    try:
        xls = pd.ExcelFile(file_path, engine=engine)
    except Exception as e:
        # --- 针对 iShares 假 Excel 的特殊拦截 ---
        if "Expected BOF record" in str(e) or "Unsupported format" in str(e):
             raise ValueError("【格式错误】该文件虽然后缀是 .xls，但实际上是 XML/文本格式（iShares 的常见问题）。\n"
                              "✅ 解决方法：请用 Excel 打开该文件，点击 '文件' -> '另存为'，选择 'Excel 工作簿 (*.xlsx)' 格式保存，\n"
                              "然后使用新保存的 .xlsx 文件进行导入。")
        raise e
    
    # 寻找 Historical Sheet
    target_sheet = None
    for s in xls.sheet_names:
        if 'historical' in s.lower():
            target_sheet = s
            break
    if not target_sheet:
        raise ValueError("未找到 'Historical' Sheet")
        
    # 寻找表头 (As Of / NAV per Share)
    df_raw = pd.read_excel(xls, sheet_name=target_sheet, header=None, nrows=20)
    header_idx = -1
    for i, row in df_raw.iterrows():
        row_str = " ".join([str(v) for v in row.values])
        if "As Of" in row_str and "NAV per Share" in row_str:
            header_idx = i
            break
    if header_idx == -1:
        raise ValueError("未在Historical表中找到 [As Of] 表头")
        
    df = pd.read_excel(xls, sheet_name=target_sheet, header=header_idx)
    
    # 映射
    col_map = {}
    for c in df.columns:
        c_str = str(c).strip()
        if c_str == "As Of": col_map[c] = 'Date'
        elif c_str == "NAV per Share": col_map[c] = 'Close'
        elif c_str == "Shares Outstanding": col_map[c] = 'Volume'
        
    return _standardize_df(df, col_map, index_code="iShare_ETF")

def _load_csi_excel(file_path):
    """中证指数官网 Excel 解析器"""
    engine = get_excel_engine(file_path)
    # 中证数据通常第一行就是表头
    df = pd.read_excel(file_path, engine=engine)
    
    # 映射
    col_map = {}
    for c in df.columns:
        c_str = str(c).strip()
        # 中证常见列名：日期Date, 收盘Close, etc. 或者是中文
        if "日期" in c_str or "Date" in c_str: col_map[c] = 'Date'
        elif "收盘" in c_str or "Close" in c_str: col_map[c] = 'Close'
        elif "开盘" in c_str or "Open" in c_str: col_map[c] = 'Open'
        elif "最高" in c_str or "High" in c_str: col_map[c] = 'High'
        elif "最低" in c_str or "Low" in c_str: col_map[c] = 'Low'
        elif "成交量" in c_str or "Volume" in c_str: col_map[c] = 'Volume'
        
    return _standardize_df(df, col_map, index_code="CSI_Index")


def _load_nsdaq_csv(file_path):
    """Nasdaq CSV 解析器"""
    df = pd.read_csv(file_path)
    col_map = {}
    for c in df.columns:
        cl = c.strip().lower()
        if 'date' in cl: col_map[c] = 'Date'
        elif 'close/last' in cl: col_map[c] = 'Close'
        elif 'open' in cl: col_map[c] = 'Open'
        elif 'high' in cl: col_map[c] = 'High'
        elif 'low' in cl: col_map[c] = 'Low'
        elif 'volume' in cl: col_map[c] = 'Volume'
    return _standardize_df(df, col_map, index_code="NDX")

def _load_bitcoin_tsv(file_path):
    """Bitcoin TSV 解析器"""
    try:
        df = pd.read_csv(file_path, sep='\t', engine='python', encoding='utf-8')
    except:
        df = pd.read_csv(file_path, sep='\t', engine='python')
    
    # 清理列名BOM
    df.columns = [str(c).strip().replace('\ufeff', '') for c in df.columns]
    
    # 假设第一列日期，第二列价格
    col_map = {df.columns[0]: 'Date', df.columns[1]: 'Close'}
    return _standardize_df(df, col_map, index_code="BTC")

def _standardize_df(df: pd.DataFrame, col_map: dict, index_code=None) -> tuple[pd.DataFrame, str]:
    """标准化与清洗 (保持不变的核心逻辑)"""
    df = df.rename(columns=col_map)
    
    # 去重
    if not df.columns.is_unique:
        df = df.loc[:, ~df.columns.duplicated()]

    # 必需列检查
    if 'Date' not in df.columns:
        # 尝试第一列兜底
        if df.shape[1] > 0:
            try:
                pd.to_datetime(df.iloc[:, 0])
                df.rename(columns={df.columns[0]: 'Date'}, inplace=True)
            except: pass
            
    if 'Date' not in df.columns:
        raise ValueError("无法识别 Date 列")

    # 类型转换
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df = df.dropna(subset=['Date'])
    
    target_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
    for col in target_cols:
        if col not in df.columns:
            if col == 'Volume': df[col] = 0.0
            elif 'Close' in df.columns: df[col] = df['Close']
            else: df[col] = 0.0
            
        if df[col].dtype == 'object':
            df[col] = df[col].astype(str).str.replace(',', '').str.replace('$', '').str.replace('"', '').replace('--', '0')
        
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)

    final_code = index_code if index_code else "Unknown"
    return df.sort_values('Date').reset_index(drop=True), final_code