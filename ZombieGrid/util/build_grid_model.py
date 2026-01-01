from typing import List, Dict, Any
from dao.grid_data_structure import GridConfig, GridRow
from dao.data_importer import DataImporter
from dao.config import SQLALCHEMY_DATABASE_URI
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from tabulate import tabulate
def generate_grid_from_input(input_params: Dict[str, Any]) -> Dict[str, Any]: 
    """
    根据输入参数生成 GridConfig 实例和对应的 GridRow 列表
    返回结构化字典，便于转 JSON 或前端使用
    """

    # Step 1: 创建 GridConfig 实例
    grid_config = GridConfig(
        name=input_params.get("name", None),
        a=input_params["a"],
        b=input_params["b"],
        first_trigger_price=input_params["first_trigger_price"],
        total_rows=input_params["total_rows"],
        buy_amount=input_params["buy_amount"]
    )

    # Step 2: 生成 GridRow 列表
    grid_rows = []

    buy_amount = input_params["buy_amount"]  # 每行金额

    for i in range(1, input_params["total_rows"] + 1):
        # 1. 计算档位值
        if i == 1:
            level_ratio = 1.0
        else:
            level_ratio = grid_rows[-1].level_ratio / (1 + input_params["a"] / 2)

        # 2. 计算跌幅
        fall_percent = level_ratio - 1

        # 3. 计算买入触发价
        buy_trigger_price = input_params["first_trigger_price"] * level_ratio

        # 4. 计算买入交易价（减滑点 0.005）
        buy_price = buy_trigger_price - 0.005

        # 5. 计算股数
        shares = buy_amount / buy_price

        # 6. 计算卖出交易价（加收益率）
        sell_price = buy_price * (1 + input_params["b"])

        # 7. 收益率和盈利金额
        yield_rate = input_params["b"]
        profit_amount = buy_amount * input_params["b"]

        # 8. 卖出触发价（这里简化为等于卖出交易价）
        sell_trigger_price = sell_price-0.005

        # 9. 创建 GridRow 实例
        row = GridRow(
            config_id=None,  
            fall_percent=fall_percent,
            level_ratio=level_ratio,
            buy_trigger_price=buy_trigger_price,
            buy_price=buy_price,
            buy_amount=buy_amount, 
            shares=shares,
            sell_trigger_price=sell_trigger_price,
            sell_price=sell_price,
            yield_rate=yield_rate,
            profit_amount=profit_amount
        )
        grid_rows.append(row)

    # Step 3: 关联配置和行（SQLAlchemy 会处理外键）
    grid_config.rows = grid_rows

    # Step 4: 返回结构化字典（可 JSON 序列化）
    result = {
        "config": {
            "id": grid_config.id if hasattr(grid_config, 'id') else None,
            "name": grid_config.name if hasattr(grid_config, 'name') else None,
            "last_modified": grid_config.last_modified if hasattr(grid_config, 'last_modified') else None,
            "a": grid_config.a,
            "b": grid_config.b,
            "first_trigger_price":grid_config.first_trigger_price,
            "total_rows": grid_config.total_rows,
            "buy_amount": grid_config.buy_amount
        },
        "rows": [
            {
                "id": row.id if hasattr(row, 'id') else None,
                "config_id": row.config_id if hasattr(row, 'config_id') else None,
                "fall_percent": row.fall_percent,
                "level_ratio": row.level_ratio,
                "buy_trigger_price": row.buy_trigger_price,
                "buy_price": row.buy_price,
                "buy_amount": row.buy_amount,
                "shares": row.shares,
                "sell_trigger_price": row.sell_trigger_price,
                "sell_price": row.sell_price,
                "yield_rate": row.yield_rate,
                "profit_amount": row.profit_amount
            }
            for row in grid_rows
        ]
    }

    return result



def save_grid_to_db(result: Dict[str, Any]):
    """将生成的网格配置和行保存到数据库"""
    data_importer = DataImporter(SQLALCHEMY_DATABASE_URI)
    success = data_importer.import_grid_model(result)
    # print(f"数据导入结果: {'成功' if success else '失败'}")
    data_importer.close()
    return success

def test_generate_grid():
    """测试函数"""
    print(" 开始测试网格生成...")

    # 测试输入参数
    input_params = {
        "a": 0.10,
        "b": 0.10,
        "first_trigger_price": 1.000,
        "total_rows": 5,
        "buy_amount": 10000.0
    }

    # 生成网格数据
    result = generate_grid_from_input(input_params)

    # 验证配置
    config = result["config"]
    assert config["a"] == 0.10
    assert config["b"] == 0.10
    assert config["first_trigger_price"] == 1.000
    assert config["total_rows"] == 5
    assert config["buy_amount"] == 10000.0
    print("配置验证通过")

    # 验证行数据
    rows = result["rows"]
    assert len(rows) == 5
    print(f"生成 {len(rows)} 行网格数据")
    
    print_structured_grid_result(result)

    # 验证数学逻辑
    first_row = rows[0]
    second_row = rows[1]

    # 验证档位值计算
    expected_level_ratio_2 = 1.0 / (1 + 0.10 / 2)
    assert abs(second_row["level_ratio"] - expected_level_ratio_2) < 1e-6
    print("档位值计算验证通过")

    # 验证买入价计算
    expected_buy_price_1 = 1.000 - 0.005
    assert abs(first_row["buy_price"] - expected_buy_price_1) < 1e-6
    print("买入价计算验证通过")

    data_importer = DataImporter(SQLALCHEMY_DATABASE_URI)
    data_importer.import_grid_model(result)
    print("导入数据量据成功")

    print("\n所有测试通过！")


def print_structured_grid_result(results: List[Dict[str, Any]]):
    if not results:
        print("⚠️ 无数据")
        return
    
    # 控制浮点数长度，避免太长太丑
    pretty_results = []
    for row in results:
        pretty_results.append({
            k: (round(v, 4) if isinstance(v, float) else v)
            for k, v in row.items()
        })
    
    headers = pretty_results[0].keys()
    table = [row.values() for row in pretty_results]
    print(tabulate(table, headers=headers, tablefmt="grid"))

if __name__ == "__main__":
    test_generate_grid()
