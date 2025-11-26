import numpy as np
import pandas as pd
from util.build_grid_model import generate_grid_from_input  # 直接导入你的函数
from util.backtest import BackTest              # 直接导入你的类
import json
def load_market_from_file(file_path="real_data.json", index_code=None):
    """从导出的JSON文件加载行情"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 如果文件包含多只指数，筛选指定指数
    if index_code:
        data = [d for d in data if d.get('index_code') == index_code]
    
    # 转换为 BackTest 需要的格式（按日期排序）
    data.sort(key=lambda x: x['日期Date'])
    
    market_data = []
    for item in data:
        market_data.append({
            'date': item['日期Date'],
            'open_price': float(item['开盘Open']),
            'high_price': float(item['最高High']),
            'low_price': float(item['最低Low']),
            'close_price': float(item['收盘Close'])
        })
    return market_data

# ================================
# 批量生成主逻辑
# ================================
if __name__ == "__main__":
    N_SAMPLES = 100
    np.random.seed(42)

    # 行情
    mock_market = load_market_from_file('data\\database_folder\\399971perf.json')

    first_price = mock_market[0]['close_price']
    first_low = mock_market[0]['low_price']
    # 输入参数范围
    a_vals = np.random.uniform(0.05, 0.30, N_SAMPLES)      # a: 5% ~ 30%
    b_vals = np.random.uniform(0.05, 0.30, N_SAMPLES)      # b: 5% ~ 30%
   # 触发价必须 ≥ 首日最低价（确保能触发买入）
    trigger_prices = np.random.uniform(first_low, first_low * 1.1, N_SAMPLES)
    model_rows = np.random.randint(5, 20, N_SAMPLES)       # 行数: 5 ~ 30
    buy_amounts = np.random.uniform(1000, 50000, N_SAMPLES) # 金额: 1k ~ 50k

    print(f"🚀 开始生成 {N_SAMPLES} 行数据（预计需要 10-30 分钟）...")
    results = []

    for i in range(N_SAMPLES):
        if i % 100 == 0:
            print(f"  📊 已处理 {i}/{N_SAMPLES} 行...")

        try:
            # 1. 生成网格策略
            input_params = {
                "a": a_vals[i],
                "b": b_vals[i],
                "first_trigger_price": trigger_prices[i],
                "total_rows": model_rows[i],
                "buy_amount": buy_amounts[i]
            }
            grid_result = generate_grid_from_input(input_params)
            grid_strategy = grid_result["rows"]
            # 2. 运行回测
            backtest = BackTest(grid_data=mock_market, grid_strategy=grid_strategy)
            metrics = backtest.run_backtest()["metrics"]
          
            # 3. 收集结果
            results.append({
                'a': a_vals[i],
                'b': b_vals[i],
                '首行买入触发价': trigger_prices[i],
                '模型行数': model_rows[i],
                '买入金额': buy_amounts[i],
                '策略 XIRR': metrics["xirr"],
                '最大回撤 (相对峰值)': metrics["max_drawdown_peak"],
                '最大回撤 (相对初始)': metrics["max_drawdown_initial"],
                '年化夏普比': metrics["sharpe"],
                '年化波动率': metrics["volatility"]
            })

        except Exception as e:
            print(f"❌ 第 {i+1} 行失败: {str(e)[:100]}")

    # 保存结果
    df = pd.DataFrame(results)
    output_file = 'OutPut.xlsx'
    df.to_excel(output_file, index=False, engine='openpyxl')
    print(f"\n✅ 成功生成 {len(df)} 行数据，保存至 '{output_file}'")