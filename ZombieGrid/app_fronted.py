# app.py
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
import sqlite3
import json
from datetime import datetime, timedelta
import random

app = FastAPI(title="ZombieGrid API", version="1.0")

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 数据库路径
DB_PATH = "data/zombiegrid.db"


def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ========== API 路由必须定义在静态文件服务之前 ==========

# ========== 基础健康检查 ==========
@app.get("/api/health")
def health_check():
    return {"status": "healthy", "message": "API is working"}


@app.get("/api/test")
def test_endpoint():
    return {"message": "Test endpoint is working"}


# ========== ZombieGrid API 路由 ==========
@app.get("/zombieGrid/api/health")
def zombie_health_check():
    return {"status": "healthy", "message": "ZombieGrid API is running"}


# 在 app.py 中添加这些缺失的路由

@app.get("/zombieGrid/api/debug/check-griddata")
def debug_check_griddata():
    """检查 GridData 表数据"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='GridData'")
        if not cursor.fetchone():
            return {"error": "GridData table does not exist"}

        # 获取数据样本
        cursor.execute("SELECT * FROM GridData LIMIT 5")
        rows = cursor.fetchall()

        data = []
        for row in rows:
            data.append(dict(row))

        # 获取总数
        cursor.execute("SELECT COUNT(*) as count FROM GridData")
        total_count = cursor.fetchone()['count']

        conn.close()
        return {
            "table": "GridData",
            "sample_data": data,
            "total_count": total_count
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/zombieGrid/api/stocks/{code}/ohlc")
def get_stock_ohlc(code: str, period: str = Query("day", enum=["day", "week", "month"])):
    """K线数据 - 修复版本"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 查询股票数据
        cursor.execute("""
            SELECT date, open_price, high_price, low_price, close_price, volume_m_shares, index_chinese_short_name
            FROM GridData 
            WHERE index_code = ? 
            ORDER BY date
        """, (code,))

        stocks = cursor.fetchall()
        if stocks:
            data = []
            for stock in stocks:
                # 处理日期格式
                date_value = stock['date']
                if hasattr(date_value, 'isoformat'):
                    date_str = date_value.isoformat()
                else:
                    date_str = str(date_value)

                data.append({
                    "date": date_str,
                    "open": round(float(stock['open_price']), 3),
                    "high": round(float(stock['high_price']), 3),
                    "low": round(float(stock['low_price']), 3),
                    "close": round(float(stock['close_price']), 3),
                    "volume": int(float(stock['volume_m_shares']) * 10000)  # 转换为手
                })

            stock_name = stocks[0]['index_chinese_short_name'] if stocks else "未知股票"
            conn.close()
            return {
                "meta": {"code": code, "name": stock_name},
                "data": data
            }

        conn.close()
    except Exception as e:
        print(f"获取K线数据错误: {e}")

    # 备用数据
    return generate_sample_ohlc_data(code)


def generate_sample_ohlc_data(code):
    """生成示例K线数据"""
    import random
    from datetime import datetime, timedelta

    start = datetime(2024, 1, 1)
    days = 100
    data = []
    price = 10.0

    for i in range(days):
        d = (start + timedelta(days=i)).date().isoformat()
        open_ = price
        close = price + random.uniform(-0.5, 0.5)
        high = max(open_, close) + random.uniform(0, 0.3)
        low = min(open_, close) - random.uniform(0, 0.3)
        vol = random.randint(1000, 5000)
        price = close

        data.append({
            "date": d,
            "open": round(open_, 3),
            "high": round(high, 3),
            "low": round(low, 3),
            "close": round(close, 3),
            "volume": vol
        })

    return {
        "meta": {"code": code, "name": "示例股票"},
        "data": data
    }


@app.post("/zombieGrid/api/strategy/generate")
def api_generate_strategy(payload: dict):
    """生成网格策略"""
    try:
        # 导入策略生成模块
        from util.build_grid_model import generate_grid_from_input

        result = generate_grid_from_input(payload)
        return result
    except Exception as e:
        print(f"生成策略错误: {e}")
        # 如果导入失败，返回示例数据
        return generate_sample_strategy(payload)


def generate_sample_strategy(payload):
    """生成示例策略数据"""
    total_rows = payload.get("total_rows", 5)
    buy_amount = payload.get("buy_amount", 10000)
    first_trigger = payload.get("first_trigger_price", 1.0)

    rows = []
    for i in range(total_rows):
        buy_trigger = first_trigger * (1 - i * 0.1)
        buy_price = buy_trigger - 0.005
        shares = buy_amount / buy_price if buy_price > 0 else 0
        sell_price = buy_price * 1.1  # 10% 收益

        rows.append({
            "id": i + 1,
            "config_id": None,
            "fall_percent": -i * 10.0,
            "level_ratio": 1.0 - i * 0.1,
            "buy_trigger_price": round(buy_trigger, 4),
            "buy_price": round(buy_price, 4),
            "buy_amount": buy_amount,
            "shares": round(shares, 2),
            "sell_trigger_price": round(sell_price - 0.005, 4),
            "sell_price": round(sell_price, 4),
            "yield_rate": 0.1,
            "profit_amount": buy_amount * 0.1
        })

    return {
        "config": {
            "id": None,
            "name": payload.get("name", "示例策略"),
            "last_modified": datetime.now().isoformat(),
            "a": payload.get("a", 0.1),
            "b": payload.get("b", 0.1),
            "first_trigger_price": first_trigger,
            "total_rows": total_rows,
            "buy_amount": buy_amount
        },
        "rows": rows
    }

@app.get("/zombieGrid/api/debug/db-status")
def debug_db_status():
    """检查数据库状态"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        tables = ['GridData', 'GridConfig', 'GridRow']
        table_status = {}

        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                count = cursor.fetchone()['count']
                table_status[table] = {"exists": True, "count": count}
            except Exception as e:
                table_status[table] = {"exists": False, "error": str(e)}

        conn.close()
        return {
            "database_status": "connected",
            "database_path": DB_PATH,
            "tables": table_status
        }
    except Exception as e:
        return {"database_status": "error", "error": str(e)}


@app.get("/zombieGrid/api/stocks/hot")
def get_hot_stocks():
    """热门股票 - 优化显示和多样性"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 获取不同的股票代码，确保多样性
        cursor.execute("""
            SELECT DISTINCT index_code, index_chinese_short_name 
            FROM GridData 
            WHERE index_code != '399971'  -- 排除中证传媒
            ORDER BY date DESC 
            LIMIT 10
        """)
        stocks = cursor.fetchall()

        hot_stocks = []
        for stock in stocks:
            # 获取最新价格和涨跌幅
            cursor.execute("""
                SELECT close_price, change_percent 
                FROM GridData 
                WHERE index_code = ? 
                ORDER BY date DESC 
                LIMIT 1
            """, (stock['index_code'],))

            latest = cursor.fetchone()
            if latest:
                change_pct = float(latest['change_percent'])
                # 优化显示：简洁的格式
                hot_stocks.append({
                    "code": stock['index_code'],
                    "name": stock['index_chinese_short_name'],
                    "latest": round(float(latest['close_price']), 2),
                    "change_pct": round(change_pct, 2)
                })

        conn.close()

        # 如果其他股票数据不足，添加中证传媒
        if len(hot_stocks) < 4:
            cursor = get_db_connection().cursor()
            cursor.execute("""
                SELECT close_price, change_percent 
                FROM GridData 
                WHERE index_code = '399971'
                ORDER BY date DESC 
                LIMIT 1
            """)
            media_stock = cursor.fetchone()
            if media_stock:
                hot_stocks.insert(0, {
                    "code": "399971",
                    "name": "中证传媒",
                    "latest": round(float(media_stock['close_price']), 2),
                    "change_pct": round(float(media_stock['change_percent']), 2)
                })

        # 如果仍然数据不足，补充示例数据
        if len(hot_stocks) < 4:
            example_stocks = [
                {"code": "000001", "name": "平安银行", "latest": 34.8, "change_pct": 1.02},
                {"code": "000858", "name": "五粮液", "latest": 165.5, "change_pct": -0.24},
                {"code": "600036", "name": "招商银行", "latest": 28.9, "change_pct": 0.68},
            ]
            hot_stocks.extend(example_stocks[:4 - len(hot_stocks)])

        return hot_stocks[:6]  # 最多显示6只

    except Exception as e:
        print(f"获取热门股票错误: {e}")
        # 返回示例数据
        return [
            {"code": "399971", "name": "中证传媒", "latest": 1200.23, "change_pct": 2.16},
            {"code": "000001", "name": "平安银行", "latest": 34.8, "change_pct": 1.02},
            {"code": "000858", "name": "五粮液", "latest": 165.5, "change_pct": -0.24},
            {"code": "600036", "name": "招商银行", "latest": 28.9, "change_pct": 0.68},
        ]


# ========== 页面路由 ==========
@app.get("/")
def serve_index():
    return FileResponse("web-frontend/index.html")


@app.get("/{page_name}")
def serve_pages(page_name: str):
    """服务前端页面"""
    valid_pages = {
        "stock": "stock.html",
        "strategy": "strategy.html",
        "backtest": "backtest.html",
        "history": "history.html"
    }

    if page_name in valid_pages:
        return FileResponse(f"web-frontend/{valid_pages[page_name]}")

    # 如果请求的是静态文件但路由没匹配，尝试直接返回
    file_path = f"web-frontend/{page_name}"
    if os.path.exists(file_path):
        return FileResponse(file_path)

    # 如果请求的是HTML文件
    if os.path.exists(f"web-frontend/{page_name}.html"):
        return FileResponse(f"web-frontend/{page_name}.html")

    raise HTTPException(status_code=404, detail="Page not found")


# ========== 静态文件服务（放在最后！） ==========
# 分别挂载各个静态目录，避免覆盖API路由
app.mount("/css", StaticFiles(directory="web-frontend/css"), name="css")
app.mount("/js", StaticFiles(directory="web-frontend/js"), name="js")
app.mount("/assets", StaticFiles(directory="web-frontend/assets"), name="assets")

# 如果还有其他静态文件目录，继续挂载
# app.mount("/images", StaticFiles(directory="web-frontend/images"), name="images")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)