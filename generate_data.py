import numpy as np
import pandas as pd
from util.build_grid_model import generate_grid_from_input, print_structured_grid_result  # 直接导入你的函数
from util.backtest import BackTest              # 直接导入你的类
from dao.db_function_library import DBSessionManager
from dao.grid_data_structure import  IndexData


def load_market_from_db():
    selected_import_id=2
    db_manager = DBSessionManager()
    try:
        with db_manager as session:
            grid_data_list = session.query(IndexData).filter(IndexData.import_id == selected_import_id).order_by(IndexData.date).all()
        if not grid_data_list: print(f"\n❌ 未找到 Import ID {selected_import_id} 的行情数据。"); input("\n按任意键返回..."); return
        grid_data = [row.to_dict() for row in grid_data_list]
        return grid_data
    except Exception as e:
        print(f"\n加载行情数据时出错: {e}"); input("\n按任意键返回..."); return

# ================================
# 批量生成主逻辑
# ================================
if __name__ == "__main__":
    N_SAMPLES = 100
    np.random.seed(42)

    # 行情
    grid_data = load_market_from_db()
    # 假设 grid_data 是 list of dict，每个 dict 有 'high_price' 或至少 'close_price'
    all_highs = [row['high_price'] for row in grid_data if 'high_price' in row]
    all_lows  = [row['low_price']  for row in grid_data]

    max_price = max(all_highs)
    min_price = min(all_lows) 

    # 输入参数范围
    a_vals = np.random.uniform(0.05, 0.30, N_SAMPLES)      # a: 5% ~ 30%
    b_vals = np.random.uniform(0.05, 0.30, N_SAMPLES)      # b: 5% ~ 30%
   # 触发价必须 ≥ 首日最低价（确保能触发买入）
    trigger_prices = np.random.uniform( min_price, max_price , N_SAMPLES)
    model_rows = np.random.randint(5, 30, N_SAMPLES)       # 行数: 5 ~ 30
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
            for idx, row in enumerate(grid_strategy):
                row["id"] = int(idx)  # ←←← 强制转换为整数
            
            
            # 2. 运行回测
            backtest = BackTest(grid_data=grid_data , grid_strategy=grid_strategy, verbose=False)
            metrics = backtest.run_backtest()["metrics"]
          
            # 3. 收集结果
            results.append({
                'a': a_vals[i],
                'b': b_vals[i],
                '首行买入触发价': trigger_prices[i],
                '模型行数': model_rows[i],
                '买入金额': buy_amounts[i],
                '策略 XIRR': metrics.get("xirr"),
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