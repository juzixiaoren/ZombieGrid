from .base_optimizer import BaseOptimizer
from bayes_opt import BayesianOptimization
import pandas as pd
import numpy as np
import sys, os
from util.build_grid_model import generate_grid_from_input
from util.backtest import BackTest

class BayesianOptimizer(BaseOptimizer):
    
    def run(self, n_iter=50) -> dict: # 默认改为 50，对齐原版
        if not self.market_data:
            print("❌ 优化器错误: 传入的行情数据为空")
            return None

        # --- 1. 数据统计 (完全对齐原版逻辑) ---
        closes = [d['close_price'] for d in self.market_data]
        df_prices = pd.Series(closes)
        
        price_mean = df_prices.mean()
        price_median = df_prices.median()
        price_25th = df_prices.quantile(0.25)
        price_75th = df_prices.quantile(0.75)
        
        min_price = df_prices.min()
        max_price = df_prices.max()
        price_range = max_price - min_price
        current_price = closes[-1]

        # --- 2. 触发价候选池 (完全对齐：13个点) ---
        # 原版逻辑：均值, 中位数, 25分位, 75分位 + 9个均匀分布点 (10%~90%)
        candidates = [
            price_mean,   
            price_median, 
            price_25th,   
            price_75th,
            min_price + price_range * 0.1,
            min_price + price_range * 0.2,
            min_price + price_range * 0.3,
            min_price + price_range * 0.4,
            min_price + price_range * 0.5,
            min_price + price_range * 0.6,
            min_price + price_range * 0.7,
            min_price + price_range * 0.8,
            min_price + price_range * 0.9
        ]
        # 注意：原版没有显式包含 current_price，我们也不加，保持严格一致
        
        # --- 3. 目标函数 (完全对齐惩罚逻辑) ---
        def objective(a, b, trigger_idx_float, lineNumber_float):
            # A. 参数映射与取整
            trigger_idx = int(round(trigger_idx_float))
            # 防止越界 (原版使用取模，这里用 min/max 更稳健，效果一致)
            trigger_idx = max(0, min(len(candidates)-1, trigger_idx))
            trigger_price = candidates[trigger_idx]
            
            lineNumber = int(round(lineNumber_float))
            lineNumber = max(10, min(50, lineNumber)) # 原版下限是 10
            
            # 限制连续参数范围 (防止贝叶斯探索时微小的浮点溢出)
            a = max(0.01, min(0.1, a))   # 原版上限 0.1
            b = max(0.01, min(0.05, b))  # 原版上限 0.05

            # 计算每格金额
            buy_amount = self.initial_capital / lineNumber
            
            params = {
                "name": "Optimization_Temp", 
                "a": a, "b": b, 
                "first_trigger_price": trigger_price, 
                "total_rows": lineNumber, 
                "buy_amount": buy_amount
            }
            
            # B. 惩罚计算 (核心差异点)
            a_penalty = 0.0
            price_penalty = 0.0
            trade_penalty = 0.0
            penalty_msgs = []
            
            # 1. a参数过小惩罚 (对齐)
            if a < 0.01: 
                a_penalty = (0.01 - a) * 10
                penalty_msgs.append(f"a过小罚:{a_penalty:.4f}")

            # 2. 触发价偏离惩罚 (对齐：>30% 才罚，系数5)
            # 原版逻辑：abs(trigger - current) / current
            deviation = abs(trigger_price - current_price) / current_price
            if deviation > 0.3:
                price_penalty = (deviation - 0.3) * 5
                penalty_msgs.append(f"偏离{deviation:.1%}罚:{price_penalty:.4f}")
            
            try:
                # 生成模型
                grid_model = generate_grid_from_input(params)
                rows = grid_model['rows'] 
                
                # 运行回测 (verbose=False 关闭打印)
                bt = BackTest(self.market_data, rows, self.initial_capital, verbose=False)
                res = bt.run_backtest()
                
                # 异常情况处理 (原版：无交易也罚)
                if not res or 'metrics' not in res:
                    return -1.0 - a_penalty - price_penalty
                    
                metrics = res['metrics']
                xirr = metrics.get('xirr')
                # 原版逻辑没显式处理 None，这里为了稳健性设为 -1
                if xirr is None: xirr = -1.0 
                
                # 3. 交易次数过少惩罚 (对齐：<3 次，线性惩罚)
                total_trades = metrics.get('buy_num', 0) + metrics.get('sell_num', 0)
                if total_trades < 3:
                    trade_penalty = (3 - total_trades) * 0.5
                    penalty_msgs.append(f"交易少({total_trades})罚:{trade_penalty:.4f}")
                
                # C. 最终得分公式 (完全对齐)
                # final_score = xirr - a_penalty - price_penalty - trade_penalty
                total_penalty = a_penalty + price_penalty + trade_penalty
                final_score = xirr - total_penalty

                # D. 详细日志
                penalty_str = f" | ⚠️ {', '.join(penalty_msgs)}" if total_penalty > 0 else ""
                print(f"Iter: a={a:.4f}, b={b:.4f}, trig={trigger_price:.2f}, rows={lineNumber}"
                      f"{penalty_str} >>> XIRR={xirr:.4f}, Score={final_score:.4f}")
                
                return final_score
                
            except Exception as e:
                # 出错返回 -1 (对齐原版)
                return -1.0

        # --- 4. 优化器配置 (完全对齐) ---
        print(f"🚀 开始贝叶斯优化，迭代次数: {n_iter} (随机探索: 10)")
        
        # 原版参数空间
        pbounds = {
            'a': (0.01, 0.1),         # 上限改回 0.1
            'b': (0.01, 0.05),        # 上限改回 0.05
            'trigger_idx_float': (0, len(candidates) - 0.1), # 对应 0-12
            'lineNumber_float': (10, 50) # 下限改回 10
        }

        optimizer = BayesianOptimization(
            f=objective,
            pbounds=pbounds,
            verbose=2, # 显示进度表
            random_state=42
        )
        
        try:
            # 原版 init_points=10
            optimizer.maximize(init_points=10, n_iter=n_iter)
        except Exception as e:
            print(f"❌ 优化器运行崩溃: {e}")
            import traceback; traceback.print_exc()
            return None
        
        if not optimizer.max:
            return None

        # --- 5. 结果提取与修正 ---
        best = optimizer.max['params']
        
        # 再次执行参数映射 (确保最终输出也是合法的)
        best_idx = int(round(best['trigger_idx_float']))
        best_idx = max(0, min(len(candidates)-1, best_idx))
        
        final_rows = int(round(best['lineNumber_float']))
        final_rows = max(10, min(50, final_rows))
        
        final_a = max(0.01, min(0.1, best['a']))
        final_b = max(0.01, min(0.05, best['b']))
        
        return {
            "a": final_a,
            "b": final_b,
            "first_trigger_price": candidates[best_idx],
            "total_rows": final_rows,
            "buy_amount": self.initial_capital / final_rows,
            "xirr_score": optimizer.max['target']
        }