import dao.db_function_library
from typing import List, Dict, Any
import pandas as pd
import numpy as np
import numpy_financial as nf
from math import sqrt
from typing import Optional
from scipy.optimize import newton
def run_backtest(grid_data: List[Dict], grid_strategy: List[Dict]) -> Dict:
    """
    回测网格交易策略的核心逻辑
    :param grid_data: 历史价格数据列表，每个元素为字典，包含以下字段：
    - date: 日期（datetime.date 或字符串）
    - index_code: 指数代码
    - index_chinese_full_name: 指数中文全称
    - index_chinese_short_name: 指数中文简称
    - index_english_full_name: 指数英文全称
    - index_english_short_name: 指数英文简称
    - open_price: 开盘价
    - high_price: 最高价
    - low_price: 最低价
    - close_price: 收盘价
    - change: 涨跌
    - change_percent: 涨跌幅(%)
    - volume_m_shares: 成交量(万手)
    - turnover: 成交金额(亿元)
    - cons_number: 样本数量
    
    :param grid_strategy: 网格交易数据列表，每个元素为字典，包含以下字段：
    - config_id: 策略配置ID
    - fall_percent: 跌幅百分比
    - level_ratio: 档位比例
    - buy_trigger_price: 买入触发价
    - buy_price: 买入交易价
    - buy_amount: 买入金额
    - shares: 买入股数
    - sell_trigger_price: 卖出触发价
    - sell_price: 卖出交易价
    - yield_rate: 收益率
    - profit_amount: 盈利金额
    :return: 回测结果，包括交易记录，收益率等数据
    """
    operate=[]  # 记录所有交易操作
    cash_balance=0.0  # 盈利现金
    max_cash_used = 0.0  # 最大占用资金
    cash_used = 0.0  # 当前占用资金
    daily_records = []   # 每日快照
    series_assert_holdings =[]  # 持仓市值
     # positions 结构：{ trigger: { strategy_id: {shares, status, ...} } }
    positions = {}
    def update_position(trigger, strategy_id, shares, status, current_date=None):
        if trigger not in positions:
            positions[trigger] = {}

        if strategy_id not in positions[trigger]:
            # 初始化
            positions[trigger][strategy_id] = {
                "shares": shares,
                "status": status,
                "last_action_date": current_date
            }
        else:
            # 更新已有格子
            pos = positions[trigger][strategy_id]
            pos["shares"] = shares
            pos["status"] = status
            if current_date is not None:
                pos["last_action_date"] = current_date
    for s in grid_strategy:
        trigger = s.get('buy_trigger_price')
        sid = s.get('id')
        if trigger is not None and sid is not None:
            positions.setdefault(trigger, {})[sid] = {
                'shares': s.get('shares', 0),
                'status': None,
                'last_action_date': None
            }
    for i, grid in enumerate(grid_data):
        date = grid['date']
        open_p = float(grid.get('open_price'))
        low_p = float(grid.get('low_price'))
        high_p = float(grid.get('high_price'))
        close_p = float(grid.get('close_price'))

        for strategy in grid_strategy:
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
                    cash_used, max_cash_used, cash_balance = operate_buy_or_sell(
                        action="买入",
                        date=date,
                        trigger=buy_trigger,
                        strategy=strategy,
                        executed_price=buy_executed_price,
                        buy_amount=buy_amount,
                        positions=positions,
                        update_position=update_position,
                        operate=operate,
                        cash_used=cash_used,
                        max_cash_used=max_cash_used,
                        is_first_day=(i==0),
                        is_last_day=(i==len(grid_data)-1),
                        cash_balance=cash_balance,
                    )
                    continue  # 建仓后跳过卖出检查
            #最后一天需要进行清仓
            elif i == len(grid_data) - 1:
                # 清仓逻辑：卖出所有持仓
                pos = positions.get(buy_trigger, {}).get(strategy.get('id'))
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
                    cash_used, max_cash_used, cash_balance = operate_buy_or_sell(
                        action="卖出",
                        date=date,
                        trigger=buy_trigger,
                        strategy=strategy,
                        executed_price=sell_executed_price,
                        buy_amount=buy_amount,
                        positions=positions,
                        update_position=update_position,
                        operate=operate,
                        cash_used=cash_used,
                        max_cash_used=max_cash_used,
                        is_first_day=(i==0),
                        is_last_day=(i==len(grid_data)-1),
                        cash_balance=cash_balance,
                    )
            # ---------- 非首日（按照常规网格触发逻辑） ----------
            else:
                # 卖出逻辑：当天曾冲高到卖出触发价且允许卖出
                if high_p >= sell_trigger and check_positions(positions, date, "卖出", buy_trigger, strategy.get('id')):
                    # 卖出触发价被触发，且允许卖出
                    if (sell_price is not None) and (low_p <= sell_price <= high_p):
                        # 卖出价在当日区间内，按卖出价成交
                        sell_executed_price = sell_price
                    else:
                        # 卖出价不在当日区间内，不成交
                        sell_executed_price = None
                    # 如果决定成交，登记持仓、记录流水、更新统计
                    if sell_executed_price is not None:
                        cash_used, max_cash_used, cash_balance = operate_buy_or_sell(
                            action="卖出",
                            date=date,
                            trigger=buy_trigger,
                            strategy=strategy,
                            executed_price=sell_executed_price,
                            buy_amount=buy_amount,
                            positions=positions,
                            update_position=update_position,
                            operate=operate,
                            cash_used=cash_used,
                            max_cash_used=max_cash_used,
                            is_first_day=(i==0),
                            is_last_day=(i==len(grid_data)-1),
                            cash_balance=cash_balance,
                        )
                #买入逻辑：当天曾下探到买入触发价且允许买入
                if low_p <= buy_trigger <= high_p and check_positions(positions, date, "买入", buy_trigger, strategy.get('id')):
                    if (buy_price is not None) and (low_p <= buy_price <= high_p):
                        buy_executed_price = buy_price
                    else:
                        # 如果没有明确的 buy_price，或者 buy_price 不在区间，
                        # 这里严谨处理：若无合适 buy_price，则不成交
                        buy_executed_price = None
                    # 如果决定成交，登记持仓、记录流水、更新统计
                    if buy_executed_price is not None:
                        cash_used, max_cash_used, cash_balance = operate_buy_or_sell(
                            action="买入",
                            date=date,
                            trigger=buy_trigger,
                            strategy=strategy,
                            executed_price=buy_executed_price,
                            buy_amount=buy_amount,
                            positions=positions,
                            update_position=update_position,
                            operate=operate,
                            cash_used=cash_used,
                            max_cash_used=max_cash_used,
                            is_first_day=(i==0),
                            is_last_day=(i==len(grid_data)-1),
                            cash_balance=cash_balance,
                    )
        # === 每日快照 ===
        assert_holdings = sum(
            pos.get("shares", 0) * close_p
            for triggers in positions.values()
            for pos in triggers.values()
        )
        series_assert_holdings.append(assert_holdings)

        daily_records.append({
            "date": date,
            "open": open_p,
            "high": high_p,
            "low": low_p,
            "close": close_p,
            "cash_used": cash_used,
            "max_cash_used": max_cash_used,
            "holding_value": assert_holdings,
            "total_value": assert_holdings + cash_balance,  # 如果有现金余额的话这里加上
        })

    df_trades = pd.DataFrame(operate)       # 交易流水
    df_daily = pd.DataFrame(daily_records)  # 每日快照
    # 交易流水
    print("\n--- 交易流水 ---")
    print(df_trades.to_string(index=False))

    print("\n--- 每日快照 ---")
    print(df_daily.to_string(index=False))

    # 计算 XIRR
    if not df_daily.empty:
        #将最大占用资金作为我们的 "初始资金"
        initial_capital = df_daily['max_cash_used'].max()
        # 计算每日账户总价值（持仓市值 + 现金余额）
        df_daily['portfolio_value'] = df_daily['total_value'] + initial_capital
        
        print("\n--- 转换后的每日账户快照 (前5条) ---")
        print(df_daily[['date', 'holding_value', 'total_value', 'portfolio_value']].head())

        value_column_for_metrics = 'portfolio_value'
    else:
        # 如果没有数据，避免错误
        initial_capital = 0
        value_column_for_metrics = 'total_value' # Fallback
    def compute_xirr_portfolio(df_daily_final, capital):
        if df_daily_final.empty or capital == 0:
            return None
        
        dates = [pd.to_datetime(df_daily_final.iloc[0]['date']), pd.to_datetime(df_daily_final.iloc[-1]['date'])]
        cashflows = [-capital, df_daily_final.iloc[-1][value_column_for_metrics]]
        
        return xirr(np.array(cashflows), dates)

    xirr_portfolio = compute_xirr_portfolio(df_daily, initial_capital)
    print("\n--- 策略表现评估 (基于账户视角) ---")
    print(f"初始资金 (最大占用资金): {initial_capital:.2f}")
    print("账户XIRR (年化内部收益率):", xirr_portfolio)

    # 2. 计算最大回撤
    mdd = max_drawdown(df_daily[value_column_for_metrics])
    print("最大回撤:", mdd)

    # 3. 计算年化夏普比率
    sharpe = compute_sharpe_from_daily(
        df_daily,
        value_col=value_column_for_metrics,
        periods_per_year=252,
        risk_free_rate_annual=0.03
    )
    print("年化夏普比,默认无风险利率为0.03:", sharpe)

    # 4. 计算年化波动率
    vol = annual_volatility(df_daily, value_col=value_column_for_metrics)
    print("年化波动率:", vol)



def check_positions(positions: Dict[float, Dict[int, Dict[str, Any]]],
                    current_date: Any, action: str, 
                    trigger_price: float, strategy_id: int) -> bool:
    """
    检查某个具体策略格子是否可以买入/卖出
    - 每个 strategy_id 唯一对应一个格子
    - 一个格子同一天不能既买入又卖出
    - 必须买过才能卖
    - 不同格子互不影响
    """
    if trigger_price not in positions or strategy_id not in positions[trigger_price]:
        return False

    pos = positions[trigger_price][strategy_id]
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
def operate_buy_or_sell(
    action: str,
    date,
    trigger,
    strategy,
    executed_price,
    buy_amount,
    positions,
    update_position,
    operate,
    cash_used,
    cash_balance,
    max_cash_used,
    is_first_day=False,
    is_last_day=False,
):
    """统一处理买入或卖出操作的函数"""
    strategy_id = strategy.get('id')
    if action == "买入" and executed_price is not None:
        actual_shares = int(buy_amount / executed_price) if executed_price > 0 else 0
        buy_amount = actual_shares * executed_price  # 实际买入金额
        update_position(
            trigger=trigger,
            strategy_id=strategy_id,
            shares=actual_shares,
            status="买入",
            current_date=date
        )
        positions[trigger][strategy_id]["buy_price"] = executed_price
        note = "首日建仓" if is_first_day else "触发买入"
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
        operate.append(row)
        cash_used += buy_amount
        max_cash_used = max(max_cash_used, cash_used)
        cash_balance -= buy_amount
        print(f"✅ [{date}] 买入 | 策略ID: {strategy_id} | 触发价: {trigger:.3f} | 成交价: {executed_price:.3f} | 买入金额: {buy_amount:.2f} | 买入股数: {actual_shares:.2f} | 备注: {note}")
        print(f"当前占用资金: {cash_used:.2f}，最大占用资金: {max_cash_used:.2f}")
        return cash_used, max_cash_used, cash_balance

    if action == "卖出" and executed_price is not None:
        pos = positions.get(trigger, {}).get(strategy_id)
        if not pos or pos.get('status') != "买入":
            print(f"警告：尝试卖出但无持仓，日期 {date}, 触发价 {trigger}, 策略ID {strategy_id}")
            return cash_used, max_cash_used, cash_balance
        sell_shares = pos.get('shares', 0) if pos else 0
        sell_amount = sell_shares * executed_price
        update_position(
            trigger=trigger,
            strategy_id=strategy_id,
            shares=0.0,
            status="卖出",
            current_date=date
        )
        note = "最后一日清仓" if is_last_day else "触发卖出"
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
        operate.append(row)
        cash_used -= pos.get('buy_price', 0) * sell_shares
        max_cash_used = max(max_cash_used, cash_used)
        cash_balance += sell_amount
        print(f"✅ [{date}] 卖出 | 策略ID: {strategy_id} | 触发价: {trigger:.3f} | 成交价: {executed_price:.3f} | 卖出金额: {sell_amount:.2f} | 卖出股数: {sell_shares:.2f} | 备注: {note}")
        print(f"当前占用资金: {cash_used:.2f}，最大占用资金: {max_cash_used:.2f}")
        return cash_used, max_cash_used, cash_balance

    return cash_used, max_cash_used, cash_balance

def max_drawdown(prices: pd.Series) -> float:
    # 累计最大值
    rolling_max = prices.cummax()
    # 回撤率序列
    drawdown = (prices - rolling_max) / rolling_max
    # 取最小值（最深回撤）
    return drawdown.min()

def xirr(cashflows, dates):
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


def compute_xirr(df_trades: pd.DataFrame, df_daily: pd.DataFrame):
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

    # 期末持仓市值（如果有）
    last_row = df_daily.iloc[-1]
    if last_row["holding_value"] > 0:
        cashflows.append(last_row["holding_value"])
        dates.append(pd.to_datetime(last_row["date"]))

    cashflows = np.array(cashflows, dtype=float)
    return xirr(cashflows, dates)
def compute_sharpe_from_daily(df_daily: pd.DataFrame,
                              value_col: str = "total_value",
                              periods_per_year: int = 252,
                              risk_free_rate_annual: float = 0.0) -> Optional[float]:
    """
    计算年化夏普比（基于 daily data）。
    - df_daily: 包含每日快照且有日期列 'date' 或索引为日期，以及 value_col
    - value_col: 用来计算净值/总资产的列名（默认 "total_value"）
    - periods_per_year: 每年周期数（daily 默认 252，交易日；可改为365）
    - risk_free_rate_annual: 年化无风险利率（小数形式，例如 0.03 表示 3%）
    返回年化夏普比（float），若数据不足或计算失败返回 None。
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
        # 如果 index 已经是日期就不处理
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

def annual_volatility(df_daily: pd.DataFrame, value_col: str = 'portfolio_value'):
    df = df_daily.copy()
    df["return"] = df[value_col].pct_change()
    returns = df["return"].dropna()
    vol = returns.std() * np.sqrt(252)
    return vol