import dao.db_function_library
from typing import List, Dict, Any

def backtest(grid_data: List[Dict], grid_strategy: List[Dict]) -> Dict:
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
    invested = 0.0  # 用于统计已投入资金
    cash=0.0 #用于统计出售所得资金
    operate=[]  # 记录所有交易操作
    maxRetracement=0.0  # 最大回撤
    max_cash_used = 0.0  # 最大占用资金
    positions = {} # 记录当前持仓，键为buy_trigger_price，值为包含id, shares, status的字典列表
    for s in grid_strategy:
        trigger = s.get('buy_trigger_price')
        if trigger is not None:  # 避免 None 键
            # 用列表存同一触发价的多个策略，避免覆盖
            positions.setdefault(trigger, []).append({
                'id': s.get('id'),
                'shares': s.get('shares', 0),
                'status': None
            })
    # 第一天进行建仓
    for i, grid in enumerate(grid_data):
        date = grid['date']
        open_p = float(grid.get('open_price'))
        low_p = float(grid.get('low_price'))
        high_p = float(grid.get('high_price'))

        for strategy in grid_strategy:
            trigger = strategy.get('buy_trigger_price')
            buy_price = strategy.get('buy_price')
            buy_amount = float(strategy.get('buy_amount', 0))

            # 跳过无效策略/触发价
            if trigger is None:
                continue

            # 检查是否允许在这个 trigger 上买（你已有的校验函数）
            if not check_positions(positions, date, "买入", trigger):
                continue

            executed_price = None # 实际成交价，None表示未成交

            if i == 0:
                # 1 开盘价已经低于等于触发价 -> 以开盘价按市价成交
                if open_p <= trigger:
                    executed_price = open_p

                # 2 否则若当日曾下探到触发价（low <= trigger <= high）
                #    则尝试以 limit 买入价成交（只有当买入价在当日区间时才认为成交）
                elif low_p <= trigger <= high_p:
                    # 买入价必须在当日区间内才认为能成交
                    if (buy_price is not None) and (low_p <= buy_price <= high_p):
                        executed_price = buy_price
                    else:
                        # 买入价不可达（例如低于当日最低或高于最高），不成交
                        executed_price = None
                else:
                    # 开盘价高于触发价且当日未跌破触发价 -> 不建仓
                    executed_price = None

            # ---------- 非首日（按照常规网格触发逻辑） ----------
            else:
                # 常规逻辑：当天曾下探到触发价且买入价在当日区间则成交
                if low_p <= trigger <= high_p:
                    if (buy_price is not None) and (low_p <= buy_price <= high_p):
                        executed_price = buy_price
                    else:
                        # 如果没有明确的 buy_price，或者 buy_price 不在区间，
                        # 可以选择用触发价作为市价成交（根据你的策略设计）
                        # 这里我们 **严谨处理**：若无合适 buy_price，则不成交
                        executed_price = None
                else:
                    executed_price = None

            # 如果决定成交，登记持仓、记录流水、更新统计
            if executed_price is not None:
                # 计算实际成交份额（用成交价计算）
                actual_shares = buy_amount / executed_price if executed_price > 0 else 0.0

                # 在 positions 中找到第一个可用 slot（status 是 None）
                pos_list = positions.get(trigger, [])
                slot = None
                for p in pos_list:
                    if p.get('status') is None:
                        slot = p
                        break

                # 如果没有可用 slot（理论上不会，但保险起见）
                if slot is None:
                    # 你可以选择 append 新 slot，或者跳过
                    slot = {
                        'id': strategy.get('id'),
                        'status': None
                    }
                    pos_list.append(slot)
                    positions[trigger] = pos_list

                # 填充 slot 信息，标记为已买（等待卖出）
                slot.update({
                    'status': 'bought',
                    'buy_price': executed_price,
                    'buy_date': date,
                    'shares': actual_shares,
                    'cost': buy_amount
                })

                # 记录流水
                operate.append({
                    "date": date,
                    "type": "买入",
                    "trigger": trigger,
                    "price": executed_price,
                    "amount": buy_amount,
                    "shares": actual_shares,
                    "note": ("首日建仓" if i == 0 else "触发买入")
                })

                # 更新统计：已投入资金 & 最大占用
                invested += buy_amount
                # 这里的现金计算基于你用 invested-cash 的方式，如果另有 cash 逻辑请调整
                max_cash_used = max(max_cash_used, invested - cash)

                # 首日已处理完这个策略，继续下一个策略
                continue
        
    for grid in grid_data[1:]:  # 从第二天开始
        date=grid['date']
        for strategy in grid_strategy:
            if strategy['buy_trigger_price'] is not None and grid['low_price'] <= strategy['buy_trigger_price']and check_positions(positions, date, "买入", strategy['buy_trigger_price']):
                # 触发买入
                operate.append({
                    "date": date,
                    "type": "买入",
                    "price": strategy['buy_price'],
                    "amount": strategy['buy_amount'],
                    "shares": strategy['shares'],
                    "note": f"触发价 {strategy['buy_trigger_price']}, 买入价 {strategy['buy_price']}, 买入股数 {strategy['shares']}"
                })
            if strategy['sell_trigger_price'] is not None and grid['high_price'] >= strategy['sell_trigger_price']:
                # 触发卖出
                operate.append({
                    "date": date,
                    "type": "卖出",
                    "price": strategy['sell_price'],
                    "amount": strategy['sell_amount'],
                    "shares": strategy['shares'],
                    "note": f"触发价 {strategy['sell_trigger_price']}, 卖出价 {strategy['sell_price']}, 卖出股数 {strategy['shares']}"
                })
def check_positions(positions: Dict[float, List[Dict[str, Any]]], current_date: Any, action: str, trigger_price: float) -> bool:
    """
    检查是否可以买入和卖出，同一天不能买入又卖出，同时已经买入的无法重复买入，已经卖出的无法重复卖出
    """
    if trigger_price not in positions:
        return False
    for pos in positions[trigger_price]:
        if action == "买入":
            if pos['status'] is None:  # 尚未买入
                pos['status'] = '买入'
                return True
        elif action == "卖出":
            if pos['status'] == '买入':  # 已买入，允许卖出
                pos['status'] = '卖出'
                return True
    return False