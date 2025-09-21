import dao.db_function_library
from typing import List, Dict, Any

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
    max_cash_used = 0.0  # 最大占用资金
    cash_used = 0.0  # 当前占用资金
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
                    cash_used, max_cash_used = operate_buy_or_sell(
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
                        is_last_day=(i==len(grid_data)-1)
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
                    cash_used, max_cash_used = operate_buy_or_sell(
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
                        is_last_day=(i==len(grid_data)-1)
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
                        cash_used, max_cash_used = operate_buy_or_sell(
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
                            is_last_day=(i==len(grid_data)-1)
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
                        cash_used, max_cash_used = operate_buy_or_sell(
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
                            is_last_day=(i==len(grid_data)-1)
                        )

            
            
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
    max_cash_used,
    is_first_day=False,
    is_last_day=False
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
        note = "首日建仓" if is_first_day else "触发买入"
        operate.append({
            "date": date,
            "type": "买入",
            "strategy_id": strategy_id,
            "trigger": trigger,
            "price": executed_price,
            "amount": buy_amount,
            "shares": actual_shares,
            "note": ("首日建仓" if is_first_day else "触发买入")
        })
        cash_used += buy_amount
        max_cash_used = max(max_cash_used, cash_used)
        print(f"✅ [{date}] 买入 | 策略ID: {strategy_id} | 触发价: {trigger:.3f} | 成交价: {executed_price:.3f} | 买入金额: {buy_amount:.2f} | 买入股数: {actual_shares:.2f} | 备注: {note}")
        print(f"当前占用资金: {cash_used:.2f}，最大占用资金: {max_cash_used:.2f}")
        return cash_used, max_cash_used

    if action == "卖出" and executed_price is not None:
        pos = positions.get(trigger, {}).get(strategy_id)
        if not pos or pos.get('status') != "买入":
            print(f"警告：尝试卖出但无持仓，日期 {date}, 触发价 {trigger}, 策略ID {strategy_id}")
            return cash_used, max_cash_used
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
        operate.append({
            "date": date,
            "type": "卖出",
            "strategy_id": strategy_id,
            "trigger": trigger,
            "price": executed_price,
            "amount": sell_amount,
            "shares": sell_shares,
            "note": ("最后一日清仓" if is_last_day else "触发卖出")
        })
        cash_used -= sell_amount
        max_cash_used = max(max_cash_used, cash_used)
        print(f"✅ [{date}] 卖出 | 策略ID: {strategy_id} | 触发价: {trigger:.3f} | 成交价: {executed_price:.3f} | 卖出金额: {sell_amount:.2f} | 卖出股数: {sell_shares:.2f} | 备注: {note}")
        print(f"当前占用资金: {cash_used:.2f}，最大占用资金: {max_cash_used:.2f}")
        return cash_used, max_cash_used

    return cash_used, max_cash_used