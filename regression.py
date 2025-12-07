import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from util.build_grid_model import generate_grid_from_input
from skopt import gp_minimize
from skopt.space import Real, Integer
from generate_data import GridDataGenerator
from util.backtest import BackTest
import os
import joblib
import warnings
from tqdm import tqdm
warnings.filterwarnings('ignore')
warnings.filterwarnings('ignore')

class StrategyOptimizer:
    def __init__(self, data_path='OutPut.xlsx', target_column='简单收益率',
                 initial_cash=None, model_path=None, save_model_path=None,market_import_id=2):
        """
        :param data_path: 输入Excel文件路径
        :param target_column: 优化目标列
        :param initial_cash: 可选，固定初始资金
        :param model_path: 可选，已训练模型文件路径，存在则加载
        :param save_model_path: 可选，训练后保存模型路径
        :param market_import_id: 市场数据导入ID
        """
        grid_data_generator = GridDataGenerator(import_id=market_import_id, n_samples=1000)
        self.load_market_from_db = grid_data_generator.load_market_from_db
        self.data_path = data_path
        self.target_column = target_column
        self.initial_cash = initial_cash
        self.model_path = model_path
        self.save_model_path = save_model_path

        # 设置优化方向
        if target_column in ['策略 XIRR', '年化夏普比','简单收益率']:
            self.optimize_mode = 'maximize'
        elif target_column in ['最大回撤 (相对峰值)', '最大回撤 (相对初始)', '年化波动率']:
            self.optimize_mode = 'minimize'
        else:
            raise ValueError(f"❌ 不支持的目标列: {target_column}")

        # 加载数据
        self.load_data()
        # 加载或训练模型
        self.load_or_train_model()

    def load_or_train_model(self):
        if self.model_path and os.path.exists(self.model_path):
            self.model = joblib.load(self.model_path)
            print(f"✅ 成功加载已训练模型: {self.model_path}")
        else:
            self.train_model()
            if self.save_model_path:
                os.makedirs(os.path.dirname(self.save_model_path), exist_ok=True)
                joblib.dump(self.model, self.save_model_path)
                print(f"✅ 模型训练完成并保存至: {self.save_model_path}")

    def train_model(self):
        self.model = RandomForestRegressor(n_estimators=200, random_state=42, n_jobs=-1)
        self.model.fit(self.X, self.y)
        print("回归模型训练完成")

    def load_data(self):
        df = pd.read_excel(self.data_path, engine='openpyxl')
        required_inputs = ['a', 'b', '首行买入触发价', '模型行数', '买入金额']
        required_outputs = ['策略 XIRR', '最大回撤 (相对峰值)', '最大回撤 (相对初始)', '年化夏普比', '年化波动率']

        missing_inputs = [col for col in required_inputs if col not in df.columns]
        if missing_inputs:
            raise ValueError(f"❌ 输入列缺失: {missing_inputs}")
        if self.target_column not in df.columns:
            raise ValueError(f"❌ 目标列 '{self.target_column}' 不在数据中")

        self.feature_names = required_inputs
        self.X = df[required_inputs]
        self.y = df[self.target_column]

        valid_mask = self.y.notna()
        self.X = self.X[valid_mask]
        self.y = self.y[valid_mask]

        print(f"数据加载完成: {len(self.X)} 行有效数据")

    def get_search_space(self):
        space = []
        for col in self.feature_names:
            if col == 'a':
                space.append(Real(0.05, 0.30, name=col))
            elif col == 'b':
                space.append(Real(0.05, 0.30, name=col))
            elif col == '首行买入触发价':
                market_data = self.load_market_from_db()
                lows  = [row['low_price']  for row in market_data]
                highs = [row.get('high_price', row['close_price']) for row in market_data]
                low_bound  = min(lows) + 0.10*(max(highs)-min(lows))
                high_bound = min(lows) + 0.60*(max(highs)-min(lows))
                space.append(Real(low_bound, high_bound, name=col))
            elif col == '模型行数':
                space.append(Integer(5, 30, name=col))
            elif col == '买入金额':
                if self.initial_cash is None:
                    space.append(Real(1000, 50000, name=col))
            else:
                low = max(0, self.X[col].min() * 0.9)
                high = self.X[col].max() * 1.1
                space.append(Real(low, high, name=col))
        return space

    def make_objective(self):
        def objective(input_values):
            input_dict = {}
            j = 0
            for col in self.feature_names:
                if col == '买入金额' and self.initial_cash is not None:
                    model_rows = int(round(input_values[self.feature_names.index('模型行数')]))
                    input_dict[col] = self.initial_cash / model_rows
                elif col == '买入金额':
                    input_dict[col] = input_values[j]
                    j += 1
                else:
                    input_dict[col] = input_values[j]
                    j += 1

            # 模型行数取整
            if '模型行数' in input_dict:
                input_dict['模型行数'] = int(round(input_dict['模型行数']))

            x_full = np.array([[input_dict[col] for col in self.feature_names]])
            pred = self.model.predict(x_full)[0]
            return -pred if self.optimize_mode == 'maximize' else pred
        return objective
    def backtest_strategy(self, best_strategy, grid_data):
        """
        使用 BackTest 运行真实行情回测
        """
        # 如果传入的是 dict，就转成 list
        if self.initial_cash is not None:
            best_strategy['买入金额'] = self.initial_cash / int(round(best_strategy['模型行数']))
        input_params = {
            "a": best_strategy['a'],
            "b": best_strategy['b'],
            "first_trigger_price": best_strategy['首行买入触发价'],
            "total_rows": best_strategy['模型行数'],
            "buy_amount": best_strategy['买入金额']
        }
        grid_result = generate_grid_from_input(input_params)
        grid_strategy = grid_result["rows"]

        # 确保每行都有 id
        for idx, row in enumerate(grid_strategy):
            row["id"] = int(idx)

        # 回测
        backtest = BackTest(grid_data=grid_data, grid_strategy=grid_strategy, verbose=True)
        metrics = backtest.run_backtest()["metrics"]
        return metrics

    def optimize_and_backtest(self, n_calls=100, n_initial_points=20, verbose=False, grid_data=None):
        """
        执行贝叶斯优化，并在真实行情回测最优策略。
        内部打印最优参数、预测值和回测指标。
        """
        print("开始优化策略参数...(预计需要30-60秒)")
        search_space = self.get_search_space()
        objective_fn = self.make_objective()
        progress_bar = tqdm(total=n_calls, desc="贝叶斯优化进度")
        def wrapped_objective(x):
            res = objective_fn(x)
            progress_bar.update(1)
            return res

        result = gp_minimize(
            func=wrapped_objective,
            dimensions=search_space,
            n_calls=n_calls,
            n_initial_points=n_initial_points,
            random_state=42,
            verbose=0
        )
        progress_bar.close()

        optimal_inputs = result.x
        optimal_value = -result.fun if self.optimize_mode == 'maximize' else result.fun

        # 构造最优策略字典
        best_strategy = {col: val for col, val in zip(self.feature_names, optimal_inputs)}
        if self.initial_cash is not None and '买入金额' in best_strategy:
            best_strategy['买入金额'] = self.initial_cash / int(round(best_strategy['模型行数']))
        best_strategy['模型行数'] = int(round(best_strategy['模型行数']))

        # 打印最优参数和预测值
        print("\n===== 贝叶斯优化得到的最优参数 =====")
        for k, v in best_strategy.items():
            print(f"{k}: {v}")
        print(f"预测目标值: {optimal_value:.6f}")

        # 回测
        if grid_data is not None:
            metrics = self.backtest_strategy(best_strategy, grid_data)
            print("\n===== 最优策略在真实行情中的表现 =====")
            for k, v in metrics.items():
                print(f"{k}: {v}")
        else:
            metrics = None

        return best_strategy, optimal_value, metrics
    def summarize_results(self, predicted_value, metrics):
        """
        对比预测值与真实回测值，并输出误差分析
        :param predicted_value: 贝叶斯优化预测值
        :param metrics: 真实回测指标字典
        """
        if metrics is None:
            print("❌ 无回测数据，无法进行总结")
            return

        print("\n===== 预测结果 vs 真实回测 =====")
        target = self.target_column

        # 中文名 -> 回测字段名映射
        field_map = {
            "简单收益率": "simple_return",
            "策略 XIRR": "xirr",
            "最大回撤 (相对峰值)": "max_drawdown_peak",
            "最大回撤 (相对初始)": "max_drawdown_initial",
            "年化夏普比": "sharpe",
            "年化波动率": "volatility"
        }

        real_value = metrics.get(field_map.get(target, target))
        print(f"目标列: {target}")
        print(f"预测值: {predicted_value:.6f}")
        if real_value is not None and not np.isnan(real_value):
            print(f"真实回测值: {real_value:.6f}")
            abs_error = abs(predicted_value - real_value)
            rel_error = abs_error / real_value if real_value != 0 else np.nan
            print(f"绝对误差: {abs_error:.6f}")
            print(f"相对误差: {rel_error:.2%}")
        else:
            print("真实回测值不可用 (None 或 nan)")

        # 可选：输出其他回测指标，便于整体评估
        extra_keys = ['策略 XIRR', '简单收益率', '最大回撤 (相对峰值)',
                    '最大回撤 (相对初始)', '年化夏普比', '年化波动率']
        print("\n其他回测指标:")
        for k in extra_keys:
            mapped_key = field_map.get(k, k)
            if mapped_key in metrics:
                print(f"  {k}: {metrics[mapped_key]}")
    def save_model(self, model_name="rf_model.pkl",save_path="./saved_models"):
        """
        保存训练好的回归模型到 models 文件夹
        """
        os.makedirs(save_path, exist_ok=True)
        model_path = os.path.join(save_path, model_name)
        joblib.dump(self.model, model_path)
        print(f"✅ 模型已保存至: {model_path}")
if __name__ == "__main__":
    # 加载行情数据
    optimizer = StrategyOptimizer(model_path="./saved_models/rf_model.pkl",data_path='OutPut.xlsx', target_column='简单收益率', initial_cash=50000, market_import_id=2)
    grid_data = optimizer.load_market_from_db()
    best_strategy, predicted_value, metrics = optimizer.optimize_and_backtest(grid_data=grid_data)
    optimizer.summarize_results(predicted_value, metrics)
    #optimizer.save_model(save_path="./saved_models")
# ----------------------------
# 使用示例
# ----------------------------
# optimizer = StrategyOptimizer(data_path='OutPut.xlsx', target_column='简单收益率', initial_cash=50000)
# best_strategy, predicted_value = optimizer.optimize()
# metrics = optimizer.backtest_strategy(best_strategy, grid_data)
# print(metrics)


# # -----------------------------
# # 9. 保存训练好的模型和结果
# # -----------------------------
# import joblib
# import json
# import os

# # 创建保存目录
# os.makedirs("saved_models", exist_ok=True)

# # 保存随机森林模型
# model_path = "saved_models/rf_model.pkl"
# joblib.dump(model, model_path)
# print(f"✅ 模型已保存至: {model_path}")

# # 保存最优参数
# required_inputs = ['a', 'b', '首行买入触发价', '模型行数', '买入金额']
# best_params = {}
# for col, val in zip(required_inputs, optimal_inputs):
#     if col == '模型行数':
#         best_params[col] = int(round(val))
#     else:
#         best_params[col] = float(val)
# best_params['最优目标值'] = float(optimal_value)
# best_params['目标列'] = TARGET_COLUMN
# best_params['优化方向'] = OPTIMIZE_MODE

# params_path = "saved_models/best_params.json"
# with open(params_path, 'w', encoding='utf-8') as f:
#     json.dump(best_params, f, ensure_ascii=False, indent=2)
# print(f"✅ 最优参数已保存至: {params_path}")

# # 保存搜索空间
# space_path = "saved_models/search_space.pkl"
# joblib.dump(search_space, space_path)
# print(f"✅ 搜索空间已保存至: {space_path}")