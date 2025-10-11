import dao.db_function_library
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
import numpy_financial as nf
import unicodedata
from math import sqrt
from scipy.optimize import newton


class BackTest:
    def __init__(self, grid_data: List[Dict], grid_strategy: List[Dict], initial_capital: Optional[float] = None):
        """
        回测网格交易策略的核心逻辑封装为类
        保留原有注释与变量名，尽量不改变外部接口命名
        """
        self.grid_data = grid_data
        self.grid_strategy = grid_strategy

        # 推断初始资金：优先使用每个格子的 buy_amount（若缺失则用 shares*buy_price）
        inferred_initial_capital = float(
            sum(
                float(s.get('buy_amount')) if s.get('buy_amount') not in (None, "")
                else (float(s.get('shares', 0)) * float(s.get('buy_price', 0)))
                for s in grid_strategy
            )
        )
        if initial_capital is None:
            self.initial_capital = float(inferred_initial_capital)

        # 以下为 run_backtest 中原本的局部变量，改造为实例属性
        self.operate = []  # 记录所有交易操作
        # 默认把推断的初始现金放入 cash_balance，保持与之前文件一致的行为
        self.cash_balance = self.initial_capital  # 现金
        self.max_cash_used = 0.0  # 最大占用资金
        self.cash_used = 0.0  # 当前占用资金
        self.daily_records: List[Dict] = []   # 每日快照
        self.series_assert_holdings: List[float] = []  # 持仓市值
        # positions 结构：{ trigger: { strategy_id: {shares, status, ...} } }
        self.positions: Dict[Any, Dict[int, Dict[str, Any]]] = {}

        # 初始化 positions（将 grid_strategy 的格子写入 positions）
        for s in self.grid_strategy:
            trigger = s.get('buy_trigger_price')
            sid = s.get('id')
            if trigger is not None and sid is not None:
                self.positions.setdefault(trigger, {})[sid] = {
                    'shares': s.get('shares', 0),
                    'status': None,
                    'last_action_date': None
                }

    def _display_width(self, s: Any) -> int:
        """返回字符串在等宽字体下的大致显示宽度（中文宽度按2算，英文按1算）"""
        s = '' if s is None else str(s)
        w = 0
        for ch in s:
            if unicodedata.east_asian_width(ch) in ('W', 'F'):
                w += 2
            else:
                w += 1
        return w

    def _pad_by_display_width(self, s: Any, width: int, align: str = 'right') -> str:
        s = '' if s is None else str(s)
        cur = self._display_width(s)
        pad_len = width - cur
        if pad_len <= 0:
            return s
        return s + ' ' * pad_len if align == 'left' else ' ' * pad_len + s

    def _print_str_table(self, str_df: pd.DataFrame, first_col_left: bool = True):
        headers = str_df.columns.tolist()
        # 计算每列的显示宽度
        col_widths = []
        for j, h in enumerate(headers):
            maxw = self._display_width(h)
            for i in range(len(str_df)):
                cell = str_df.iat[i, j]
                w = self._display_width(cell)
                if w > maxw:
                    maxw = w
            col_widths.append(maxw)

        # 头部（第一列左对齐，其它右对齐）
        header_line = "  ".join(
            self._pad_by_display_width(headers[j], col_widths[j], align='left' if (j == 0 and first_col_left) else 'right')
            for j in range(len(headers))
        )
        sep_line = "  ".join("-" * col_widths[j] for j in range(len(headers)))
        print(header_line)
        print(sep_line)

        # 每行
        for i in range(len(str_df)):
            row_cells = []
            for j, col in enumerate(headers):
                align = 'left' if (j == 0 and first_col_left) else 'right'
                row_cells.append(self._pad_by_display_width(str_df.iat[i, j], col_widths[j], align=align))
            print("  ".join(row_cells))

    def print_trades_and_daily(self, df_trades: pd.DataFrame, df_daily: pd.DataFrame):
        """格式化并中文化打印交易流水与每日快照（中文对齐已修正）"""
        # ---- 交易流水 ----
        print("\n--- 交易流水 ---")
        if df_trades.empty:
            print("无交易流水")
        else:
            df_trades_display = df_trades.copy()
            # 数值列格式化（千分位，两位小数）
            num_cols = [c for c in df_trades_display.columns if df_trades_display[c].dtype.kind in 'fiu']
            for c in num_cols:
                df_trades_display[c] = df_trades_display[c].apply(lambda x: f"{x:,.2f}" if pd.notna(x) else "")
            str_df_trades = df_trades_display.fillna('').astype(str)
            # 交易表：第一列左对齐（通常是时间/代码），其余右对齐
            self._print_str_table(str_df_trades, first_col_left=True)

        # ---- 每日快照 ----
        print("\n--- 每日快照 ---")
        if df_daily.empty:
            print("无每日快照")
        else:
            df_show = df_daily.rename(columns={
                "date": "日期",
                "open": "开盘",
                "high": "最高",
                "low": "最低",
                "close": "收盘",
                "cash_used": "占用资金",
                "max_cash_used": "最大占用资金",
                "holding_value": "持仓市值",
                "cash_balance": "现金余额",
                "total_value": "总资产",
            }).copy()

            # 格式化数值列：千分位、两位小数；保留日期字段原样
            for col in df_show.columns:
                if col == "日期":
                    continue
                df_show[col] = df_show[col].apply(
                    lambda v: f"{v:,.2f}" if pd.notna(v) and isinstance(v, (int, float, np.integer, np.floating))
                    else (v if pd.notna(v) else "")
                )

            str_df = df_show.fillna('').astype(str)
            # 每日快照：'日期' 左对齐，其它列右对齐
            self._print_str_table(str_df, first_col_left=True)

    def xirr(self, cashflows, dates):
        """计算XIRR，cashflows为现金流数组，dates为对应日期数组"""
        dates = pd.to_datetime(dates)
        t0 = dates.min()
        years = (dates - t0).days / 365.0

        def npv(r):
            return np.sum(cashflows / (1 + r) ** years)

        try:
            return newton(npv, 0.1)  # 初始猜测 10%
        except RuntimeError:
            return np.nan

    def compute_xirr(self, df_trades: pd.DataFrame, df_daily: pd.DataFrame):
        """根据交易流水和每日净值计算策略XIRR"""
        cashflows = []
        dates = []

        # 交易流水
        for _, row in df_trades.iterrows():
            if row["action"] == "买入":
                cashflows.append(-row["amount"])
                dates.append(pd.to_datetime(row["date"]))
            elif row["action"] == "卖出":
                cashflows.append(row["amount"])
                dates.append(pd.to_datetime(row["date"]))
                
                
        if len(cashflows) < 2:
            return None

        # 根据日期排序现金流
        cf_df = pd.DataFrame({"date": pd.to_datetime(dates), "cf": np.array(cashflows, dtype=float)})
        cf_df = cf_df.sort_values("date")
        cashflows_sorted = cf_df["cf"].to_numpy(dtype=float)
        dates_sorted = cf_df["date"].to_list()

        # 必须同时包含正负现金流
        if not (np.any(cashflows_sorted > 0) and np.any(cashflows_sorted < 0)):
            return None

        try:
            irr = self.xirr(cashflows_sorted, dates_sorted)
            if np.isnan(irr):
                return None
            return float(irr)
        except Exception:
            return None

    def max_drawdown(self, prices: pd.Series) -> Optional[float]:
        if prices is None or prices.empty:
            return None
        # 累计最大值
        rolling_max = prices.cummax()
        # 回撤率序列
        drawdown = (prices - rolling_max) / rolling_max
        # 取最小值（最深回撤）
        return drawdown.min()

    def compute_sharpe_from_daily(self, df_daily: pd.DataFrame,
                                  value_col: str = "total_value",
                                  periods_per_year: int = 252,
                                  risk_free_rate_annual: float = 0.0) -> Optional[float]:
        """
        计算年化夏普比（基于 daily data）。
        """
        # --- 准备净值序列 ---
        if value_col not in df_daily.columns:
            raise ValueError(f"df_daily 中没有列 '{value_col}'")

        # 确保按日期排序
        df = df_daily.copy()
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date").set_index("date")
        else:
            df = df.sort_index()

        series = df[value_col].astype(float).dropna()

        # 需要至少两天数据才能计算收益率
        if len(series) < 2:
            return None

        # --- 计算周期收益率（这里用 simple returns） ---
        returns = series.pct_change().dropna()

        # --- 无风险利率按周期拆分（年化->周期） ---
        rf_per_period = (1 + risk_free_rate_annual) ** (1.0 / periods_per_year) - 1.0

        # --- 超额收益 ---
        excess_returns = returns - rf_per_period

        # 若标准差为 0 则无法计算
        std = excess_returns.std(ddof=1)
        if std == 0 or np.isnan(std):
            return None

        mean_excess = excess_returns.mean()

        # 年化：乘以 sqrt(N_periods_per_year)
        sharpe_annual = (mean_excess / std) * sqrt(periods_per_year)
        return float(sharpe_annual)

    def annual_volatility(self, df_daily: pd.DataFrame, value_col: str = 'portfolio_value', periods_per_year: int = 252):
        # 输入校验与排序
        if df_daily is None or df_daily.empty or value_col not in df_daily.columns:
            return None
        df = df_daily.copy()
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date").set_index("date")
        else:
            df = df.sort_index()

        series = df[value_col].astype(float).dropna()
        if len(series) < 2:
            return None

        # 使用简单收益；样本标准差 ddof=1 与 compute_sharpe_from_daily 保持一致
        returns = series.pct_change().dropna()
        vol = returns.std(ddof=1) * np.sqrt(periods_per_year)
        return float(vol)

    def check_positions(self, current_date: Any, action: str, trigger_price: float, strategy_id: int) -> bool:
        """
        检查某个具体策略格子是否可以买入/卖出
        - 每个 strategy_id 唯一对应一个格子
        - 一个格子同一天不能既买入又卖出
        - 必须买过才能卖
        - 不同格子互不影响
        """
        if trigger_price not in self.positions or strategy_id not in self.positions[trigger_price]:
            return False

        pos = self.positions[trigger_price][strategy_id]
        last_date = pos.get("last_action_date")
        status = pos.get("status")

        if action == "买入":
            if status is None or status == "卖出":  # 从未买过或已卖出
                return True

        elif action == "卖出":
            if status == "买入" and last_date != current_date:
                # 必须已经买过，且不能和买入是同一天
                return True

        return False

    def operate_buy_or_sell(self,
                            action: str,
                            date,
                            trigger,
                            strategy,
                            executed_price,
                            buy_amount,
                            is_first_day=False,
                            is_last_day=False):
        """统一处理买入或卖出操作的函数（保留原变量和打印样式）"""
        strategy_id = strategy.get('id')
        if action == "买入" and executed_price is not None:
            actual_shares = int(buy_amount / executed_price) if executed_price > 0 else 0
            buy_amount = actual_shares * executed_price  # 实际买入金额
            self.update_position(trigger=trigger, strategy_id=strategy_id, shares=actual_shares, status="买入", current_date=date)
            self.positions[trigger][strategy_id]["buy_price"] = executed_price
            row = {
                "date": date,
                "action": "买入",
                "strategy_id": strategy_id,
                "trigger": trigger,
                "executed_price": executed_price,
                "shares": actual_shares,
                "amount": buy_amount,
                "note": ("首日建仓" if is_first_day else "触发买入")
            }
            self.operate.append(row)
            self.cash_used += buy_amount
            self.max_cash_used = max(self.max_cash_used, self.cash_used)
            self.cash_balance -= buy_amount
            print(f"✅ [{date}] 买入 | 策略ID: {strategy_id} | 触发价: {trigger:.3f} | 成交价: {executed_price:.3f} | 买入金额: {buy_amount:.2f} | 买入股数: {actual_shares:.2f}")
            print(f"当前占用资金: {self.cash_used:.2f}，最大占用资金: {self.max_cash_used:.2f}")
            return self.cash_used, self.max_cash_used, self.cash_balance

        if action == "卖出" and executed_price is not None:
            pos = self.positions.get(trigger, {}).get(strategy_id)
            if not pos or pos.get('status') != "买入":
                print(f"警告：尝试卖出但无持仓，日期 {date}, 触发价 {trigger}, 策略ID {strategy_id}")
                return self.cash_used, self.max_cash_used, self.cash_balance
            sell_shares = pos.get('shares', 0) if pos else 0
            sell_amount = sell_shares * executed_price
            self.update_position(trigger=trigger, strategy_id=strategy_id, shares=0.0, status="卖出", current_date=date)
            row = {
                "date": date,
                "action": "卖出",
                "strategy_id": strategy_id,
                "trigger": trigger,
                "executed_price": executed_price,
                "shares": sell_shares,
                "amount": sell_amount,
                "note": ("最后一日清仓" if is_last_day else "触发卖出")
            }
            self.operate.append(row)
            self.cash_used -= pos.get('buy_price', 0) * sell_shares
            self.max_cash_used = max(self.max_cash_used, self.cash_used)
            self.cash_balance += sell_amount
            print(f"✅ [{date}] 卖出 | 策略ID: {strategy_id} | 触发价: {trigger:.3f} | 成交价: {executed_price:.3f} | 卖出金额: {sell_amount:.2f} | 卖出股数: {sell_shares:.2f}")
            print(f"当前占用资金: {self.cash_used:.2f}，最大占用资金: {self.max_cash_used:.2f}")
            return self.cash_used, self.max_cash_used, self.cash_balance

        return self.cash_used, self.max_cash_used, self.cash_balance

    def update_position(self, trigger, strategy_id, shares, status, current_date=None):
        if trigger not in self.positions:
            self.positions[trigger] = {}

        if strategy_id not in self.positions[trigger]:
            # 初始化
            self.positions[trigger][strategy_id] = {
                "shares": shares,
                "status": status,
                "last_action_date": current_date
            }
        else:
            # 更新已有格子
            pos = self.positions[trigger][strategy_id]
            pos["shares"] = shares
            pos["status"] = status
            if current_date is not None:
                pos["last_action_date"] = current_date

    def run_backtest(self) -> Dict:
        """
        回测主流程（保留原 run_backtest 的注释与行为）
        """
        for i, grid in enumerate(self.grid_data):
            date = grid['date']
            open_p = float(grid.get('open_price'))
            low_p = float(grid.get('low_price'))
            high_p = float(grid.get('high_price'))
            close_p = float(grid.get('close_price'))

            for strategy in self.grid_strategy:
                buy_trigger = strategy.get('buy_trigger_price')
                buy_price = strategy.get('buy_price')
                sell_trigger = strategy.get('sell_trigger_price')
                sell_price = strategy.get('sell_price')
                buy_amount = float(strategy.get('buy_amount', 0))

                # 跳过无效策略/触发价
                if buy_trigger is None:
                    continue

                buy_executed_price = None # 实际成交价，None表示未成交
                sell_executed_price = None # 实际卖出价，None表示未成交
                # 第一天进行建仓
                if i == 0:
                    #检查是否允许买入
                    # 1 开盘价已经低于等于触发价 -> 以开盘价按市价成交
                    if open_p <= buy_trigger and open_p <= buy_price:
                        buy_executed_price = open_p

                    # 2 否则若当日曾下探到触发价（low <= buy_trigger <= high）
                    #    则尝试以 limit 买入价成交（只有当买入价在当日区间时才认为成交）
                    elif low_p <= buy_trigger <= high_p:
                        # 买入价必须在当日区间内才认为能成交
                        if (buy_price is not None) and (low_p <= buy_price <= high_p):
                            buy_executed_price = buy_price
                        else:
                            # 买入价不可达（例如低于当日最低或高于最高），不成交
                            buy_executed_price = None
                    else:
                        # 开盘价高于触发价且当日未跌破触发价 -> 不建仓
                        buy_executed_price = None
                    if buy_executed_price is not None:
                        self.operate_buy_or_sell(
                            action="买入",
                            date=date,
                            trigger=buy_trigger,
                            strategy=strategy,
                            executed_price=buy_executed_price,
                            buy_amount=buy_amount,
                            is_first_day=(i==0),
                            is_last_day=(i==len(self.grid_data)-1),
                        )
                        continue  # 建仓后跳过卖出检查
                #最后一天需要进行清仓
                elif i == len(self.grid_data) - 1:
                    # 清仓逻辑：卖出所有持仓
                    pos = self.positions.get(buy_trigger, {}).get(strategy.get('id'))
                    if pos and pos.get('status') == "买入":
                        if (open_p>= sell_trigger) and (open_p >= sell_price):
                            sell_executed_price = open_p
                        elif high_p >= sell_trigger:
                            if (sell_price is not None) and (low_p <= sell_price <= high_p):
                                sell_executed_price = sell_price
                            else:
                                sell_executed_price = close_p
                        else:
                            sell_executed_price = close_p
                    else:
                        sell_executed_price = None
                    if sell_executed_price is not None:
                        self.operate_buy_or_sell(
                            action="卖出",
                            date=date,
                            trigger=buy_trigger,
                            strategy=strategy,
                            executed_price=sell_executed_price,
                            buy_amount=buy_amount,
                            is_first_day=(i==0),
                            is_last_day=(i==len(self.grid_data)-1),
                        )
                # ---------- 非首日（按照常规网格触发逻辑） ----------
                else:
                    # 卖出逻辑：当天曾冲高到卖出触发价且允许卖出
                    if high_p >= sell_trigger and self.check_positions(date, "卖出", buy_trigger, strategy.get('id')):
                        # 卖出触发价被触发，且允许卖出
                        if (sell_price is not None) and (low_p <= sell_price <= high_p):
                            # 卖出价在当日区间内，按卖出价成交
                            sell_executed_price = sell_price
                        else:
                            # 卖出价不在当日区间内，不成交
                            sell_executed_price = None
                        # 如果决定成交，登记持仓、记录流水、更新统计
                        if sell_executed_price is not None:
                            self.operate_buy_or_sell(
                                action="卖出",
                                date=date,
                                trigger=buy_trigger,
                                strategy=strategy,
                                executed_price=sell_executed_price,
                                buy_amount=buy_amount,
                                is_first_day=(i==0),
                                is_last_day=(i==len(self.grid_data)-1),
                            )
                    #买入逻辑：当天曾下探到买入触发价且允许买入
                    if low_p <= buy_trigger <= high_p and self.check_positions(date, "买入", buy_trigger, strategy.get('id')):
                        if (buy_price is not None) and (low_p <= buy_price <= high_p):
                            buy_executed_price = buy_price
                        else:
                            # 如果没有明确的 buy_price，或者 buy_price 不在区间，
                            # 这里严谨处理：若无合适 buy_price，则不成交
                            buy_executed_price = None
                        # 如果决定成交，登记持仓、记录流水、更新统计
                        if buy_executed_price is not None:
                            self.operate_buy_or_sell(
                                action="买入",
                                date=date,
                                trigger=buy_trigger,
                                strategy=strategy,
                                executed_price=buy_executed_price,
                                buy_amount=buy_amount,
                                is_first_day=(i==0),
                                is_last_day=(i==len(self.grid_data)-1),
                            )

            # === 每日快照 ===
            assert_holdings = sum(
                pos.get("shares", 0) * close_p
                for triggers in self.positions.values()
                for pos in triggers.values()
            )
            self.series_assert_holdings.append(assert_holdings)

            self.daily_records.append({
                "date": date,
                "open": open_p,
                "high": high_p,
                "low": low_p,
                "close": close_p,
                "cash_used": self.cash_used,
                "max_cash_used": self.max_cash_used,
                "holding_value": assert_holdings,
                "cash_balance": self.cash_balance,
                "total_value": assert_holdings + self.cash_balance,
            })

        df_trades = pd.DataFrame(self.operate)       # 交易流水
        df_daily = pd.DataFrame(self.daily_records)  # 每日快照
        # 交易流水
        self.print_trades_and_daily(df_trades, df_daily)

        # 计算 XIRR、最大回撤、夏普比等指标
        #计算XIRR
        xirr_portfolio = None
        # 使用 total_value 作为账户净值
        if not df_daily.empty:
            value_column_for_metrics = "total_value"
            try:
                xirr_portfolio = self.compute_xirr(df_trades, df_daily)
            except Exception:
                xirr_portfolio = None
        else:
            value_column_for_metrics = "total_value"
            xirr_portfolio = None
        print("策略XIRR:", xirr_portfolio)
        # 2. 计算最大回撤
        mdd = self.max_drawdown(df_daily[value_column_for_metrics]) if not df_daily.empty else None
        print("最大回撤:", mdd)

        # 3. 计算年化夏普比率
        sharpe = self.compute_sharpe_from_daily(
            df_daily,
            value_col=value_column_for_metrics,
            periods_per_year=252,
            risk_free_rate_annual=0.03
        )
        print("年化夏普比,默认无风险利率为0.03:", sharpe)

        # 4. 计算年化波动率
        vol = self.annual_volatility(df_daily, value_col=value_column_for_metrics)
        print("年化波动率:", vol)

        return {
            "df_trades": df_trades,
            "df_daily": df_daily,
            "metrics": {
                "initial_capital": self.initial_capital,
                "xirr": xirr_portfolio,
                "max_drawdown": mdd,
                "sharpe": sharpe,
                "volatility": vol,
            }
        }