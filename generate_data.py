import numpy as np
import pandas as pd
from util.build_grid_model import generate_grid_from_input, print_structured_grid_result  # 直接导入你的函数
from util.backtest import BackTest              # 直接导入你的类
from dao.db_function_library import DBSessionManager
from dao.grid_data_structure import  IndexData
from tqdm import tqdm

class GridDataGenerator:
    def __init__(self, import_id=2, n_samples=10000, seed=42):
        """
        :param import_id: 数据库中行情ID
        :param n_samples: 生成策略样本数量
        :param seed: 随机种子，保证可复现
        """
        self.import_id = import_id
        self.n_samples = n_samples
        self.seed = seed
        np.random.seed(seed)
        self.grid_data = self.load_market_from_db()
        if not self.grid_data:
            raise ValueError(f"未找到 Import ID {import_id} 的行情数据")
        self.low_bound, self.high_bound = self.compute_trigger_bounds()
    
    def load_market_from_db(self):
        db_manager = DBSessionManager()
        try:
            with db_manager as session:
                grid_data_list = session.query(IndexData)\
                    .filter(IndexData.import_id == self.import_id)\
                    .order_by(IndexData.date).all()
            if not grid_data_list:
                print(f"\n❌ 未找到 Import ID {self.import_id} 的行情数据。")
                return []
            grid_data = [row.to_dict() for row in grid_data_list]
            return grid_data
        except Exception as e:
            print(f"\n加载行情数据时出错: {e}")
            return []

    def compute_trigger_bounds(self):
        highs = [row['high_price'] for row in self.grid_data if 'high_price' in row]
        lows  = [row['low_price'] for row in self.grid_data]
        min_p = min(lows)
        max_p = max(highs)
        # 10% ~ 60% 的网格低位区间
        low_bound  = min_p + (max_p - min_p) * 0.10
        high_bound = min_p + (max_p - min_p) * 0.60
        return low_bound, high_bound

    def generate_samples(self):
        """批量生成策略参数并回测"""
        a_vals = np.random.uniform(0.05, 0.30, self.n_samples)
        b_vals = np.random.uniform(0.05, 0.30, self.n_samples)
        trigger_prices = np.random.uniform(self.low_bound, self.high_bound, self.n_samples)
        model_rows = np.random.randint(5, 30, self.n_samples)
        buy_amounts = np.random.uniform(1000, 50000, self.n_samples)

        print(f"🚀 开始生成 {self.n_samples} 行数据（预计需要 10-30 分钟）...")
        results = []

        for i in tqdm(range(self.n_samples), desc="生成与回测进度"):
            try:
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
                    row["id"] = int(idx)

                backtest = BackTest(grid_data=self.grid_data, grid_strategy=grid_strategy, verbose=False)
                metrics = backtest.run_backtest()["metrics"]

                results.append({
                    'a': a_vals[i],
                    'b': b_vals[i],
                    '首行买入触发价': trigger_prices[i],
                    '模型行数': model_rows[i],
                    '买入金额': buy_amounts[i],
                    '简单收益率': metrics.get("simple_return"),
                    '策略 XIRR': metrics.get("xirr"),
                    '最大回撤 (相对峰值)': metrics.get("max_drawdown_peak"),
                    '最大回撤 (相对初始)': metrics.get("max_drawdown_initial"),
                    '年化夏普比': metrics.get("sharpe"),
                    '年化波动率': metrics.get("volatility")
                })
            except Exception as e:
                tqdm.write(f"❌ 第 {i+1} 行失败: {str(e)[:100]}")

        df = pd.DataFrame(results)
        output_file = f'OutPut_{self.import_id}.xlsx'
        df.to_excel(output_file, index=False, engine='openpyxl')
        print(f"\n✅ 成功生成 {len(df)} 行数据，保存至 '{output_file}'")
        return df

if __name__ == "__main__":
    generator = GridDataGenerator(import_id=2, n_samples=10000)
    df = generator.generate_samples()