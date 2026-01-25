"""
本部分是和GridTrading项目合并阶段的前端部分，涉及跨项目文件夹的import。
"""

# service/cli.py
import os
import time
import sys
from typing import List, Dict, Any, Optional
from tabulate import tabulate
from datetime import datetime
import pandas as pd

try:
    # Dao
    from dao.grid_data_structure import GridConfig, GridRow, ImportedFiles, IndexData
    from dao.db_function_library import DBSessionManager, init_db
    from dao.data_importer import DataImporter
    from dao.config import SQLALCHEMY_DATABASE_URI

    # Util
    from util.build_grid_model import generate_grid_from_input, print_structured_grid_result, save_grid_to_db
    from util.init_to_json import excel_to_json 
    from util.backtest import BackTest 
    
    # Optimization [新增]
    from optimization import get_optimizer

except ImportError as e:
    print(f"启动时导入模块失败: {e}")
    print("请确保在项目根目录运行，并且 Conda 环境已激活且安装了所有依赖。")
    input("按回车键退出...") 
    sys.exit(1)

# --- 辅助函数 ---
def clear():
    """清屏函数"""
    os.system('cls' if os.name == 'nt' else 'clear')

def display_list_with_index(items: list, display_func=None, show_empty_message=True):
    """显示带序号的列表，返回列表是否为空"""
    if not items:
        if show_empty_message:
            print("\n列表为空。")
        return False 

    if display_func:
        for i, item in enumerate(items):
            print(f"{i+1}. {display_func(item)}")
    else:
        for i, item in enumerate(items):
            print(f"{i+1}. {item}")
    return True 

def get_index_input(max_index: int) -> int | str | None:
    """获取用户输入的序号，处理'b'和无效输入"""
    if max_index <= 0:
        while True:
            choice = input(f"\n按 b 返回: ").strip().lower()
            if choice == 'b': return 'b'
            else: print("❌ 无效输入。")

    while True:
        choice = input(f"\n请选择序号（按 b 返回）: ").strip().lower()
        if choice == 'b': return 'b'
        try:
            index_num = int(choice)
            if 1 <= index_num <= max_index: return index_num
            else: print(f"❌ 无效序号，请输入不大于 {max_index} 的数字。")
        except ValueError:
            print("❌ 无效输入，请输入数字序号或 b。")

def confirm_action(prompt: str) -> bool:
    """要求用户确认操作"""
    while True:
        choice = input(f"{prompt} (y/n): ").strip().lower()
        if choice == 'y': return True
        elif choice == 'n': return False
        else: print("请输入 y 或 n。")

def input_with_cancel(prompt: str, input_type=str, min_value=None, max_value=None):
    """封装输入逻辑，允许输入 'b' 取消"""
    while True:
        value_str = input(prompt).strip()
        if value_str.lower() == 'b': return 'b'
        try:
            if input_type == float:
                value = float(value_str)
                if min_value is not None and value < min_value: print(f"❌ 值必须 ≥ {min_value}"); continue
                if max_value is not None and value > max_value: print(f"❌ 值必须 ≤ {max_value}"); continue
                return value
            elif input_type == int:
                value = int(value_str)
                if min_value is not None and value < min_value: print(f"❌ 值必须 ≥ {min_value}"); continue
                if max_value is not None and value > max_value: print(f"❌ 值必须 ≤ {max_value}"); continue
                return value
            elif input_type == str:
                return value_str
        except ValueError:
            if input_type == float or input_type == int:
                print(f"❌ 请输入一个有效的数字{' (整数)' if input_type == int else ''}。")
            else: print("❌ 无效输入。")

# --- 主菜单和子菜单处理函数 ---
def run_cli():
    """运行命令行界面的主函数"""
    if init_db() is None:
        print("数据库初始化检查失败，无法启动程序。")
        input("按回车键退出...")
        return

    main_menu = {
        '1': ('策略管理', handle_strategy_management),
        '2': ('回测数据管理', handle_data_management),
        '3': ('从回测数据推荐网格策略参数', handle_get_best_params),
        '4': ('开始回测', handle_backtest),
        'c': ('退出', None)
    }

    while True:
        clear()
        print("【网格交易神器】\n")
        for key, (label, _) in main_menu.items():
            print(f"{key}. {label}")

        choice = input("\n输入选项: ").strip().lower()

        if choice == 'c':
            print("\n👋 再见")
            break

        if choice in main_menu:
            label, action = main_menu[choice]
            if action:
                try: action()
                except Exception as e:
                    print(f"\n⚠️ 功能执行时遇到错误: {e}")
                    input("\n按任意键返回主菜单...")
        else:
            print("\n❌ 无效选项，请重新输入！")
            time.sleep(0.5)

def handle_strategy_management():
    """处理策略管理子菜单"""
    strategy_menu = {
        '1': ('新建策略', handle_create_strategy),
        '2': ('查看已有策略', handle_view_strategies),
        '3': ('删除策略', handle_delete_strategy),
    }
    while True:
        clear()
        print("【网格交易神器】>【策略管理】\n")
        for key, (label, _) in strategy_menu.items():
            print(f"{key}. {label}")

        choice = input("\n输入选项（按 b 返回）: ").strip().lower()
        if choice == 'b': break
        if choice in strategy_menu:
            label, action = strategy_menu[choice]
            if action:
                try: action()
                except Exception as e:
                    print(f"\n⚠️ 功能执行时遇到错误: {e}")
                    input("\n按任意键返回策略管理菜单...")
        else:
            print("\n❌ 无效选项，请重新输入！")
            time.sleep(0.5)

def handle_data_management():
    """处理回测数据管理子菜单"""
    data_menu = {
        '1': ('导入行情数据', handle_import_market_data),
        '2': ('查看现有数据', handle_view_market_data),
        '3': ('删除行情数据 (按导入批次)', handle_delete_market_data),
    }
    while True:
        clear()
        print("【网格交易神器】>【回测数据管理】\n")
        for key, (label, _) in data_menu.items():
            print(f"{key}. {label}")

        choice = input("\n输入选项（按 b 返回）: ").strip().lower()
        if choice == 'b': break
        if choice in data_menu:
            label, action = data_menu[choice]
            if action:
                try: action()
                except Exception as e:
                    print(f"\n⚠️ 功能执行时遇到错误: {e}")
                    input("\n按任意键返回数据管理菜单...")
        else:
            print("\n❌ 无效选项，请重新输入！")
            time.sleep(0.5)

# --- 具体功能实现 ---

def handle_create_strategy():
    """新建策略"""
    clear()
    print("【网格交易神器】>【策略管理】>【新建策略】")
    print("（按 b 取消）\n")
    params = {}
    prompts = [
        ("name", "[1/6] 请输入策略名称（可选）: ", str, None, None),
        ("a", "[2/6] 请输入波动捕捉大小参数 a (0.01~0.30): ", float, 0.01, 0.30),
        ("b", "[3/6] 请输入每行收益率参数 b (0.01~0.30): ", float, 0.01, 0.30),
        ("first_trigger_price", "[4/6] 请输入首个触发价 (例如 1.000): ", float, 0.0001, None),
        ("total_rows", "[5/6] 请输入总行数 (例如 5): ", int, 1, None),
        ("buy_amount", "[6/6] 请输入每次买入金额 (例如 10000.0): ", float, 0.01, None)
    ]

    for key, prompt, type, min_val, max_val in prompts:
        value = input_with_cancel(prompt, type, min_val, max_val)
        if value == 'b': print("\n操作已取消。"); time.sleep(0.5); return
        if key == "name":
            if isinstance(value, str) and value.lower() == 'b': return
            params[key] = value if value else None
        else: params[key] = value

    try:
        result = generate_grid_from_input(params)
        print("\n--- 生成的策略数据预览 ---")
        print_structured_grid_result(result["rows"]) 

        if confirm_action("\n是否保存该策略？"):
            if save_grid_to_db(result): print("✅ 策略已保存到数据库！")
            else: print("❌ 保存策略失败。") 
        else: print("👌 策略不保存。")
    except Exception as e:
         print(f"\n⚠️ 生成或保存策略时出错: {e}")
    input("\n按任意键返回策略管理菜单...")


def handle_view_strategies():
    """查看策略"""
    db_manager = DBSessionManager()
    try:
        with db_manager as session:
            configs = session.query(GridConfig).order_by(GridConfig.id).all()
    except Exception as e:
        print(f"查询出错: {e}"); input("..."); return

    def display_config(cfg: GridConfig):
        last = cfg.last_modified.strftime("%Y-%m-%d") if cfg.last_modified else "无"
        name = cfg.name if cfg.name else "无名称"
        return f"ID: {cfg.id:<4} | {name:<15} | a={cfg.a:<4.2f} | b={cfg.b:<4.2f} | 行:{cfg.total_rows:<3} | {last}"

    clear()
    print("【网格交易神器】>【策略管理】>【查看已有策略】\n")
    display_list_with_index(configs, display_config)
    
    choice = get_index_input(len(configs))
    if choice == 'b' or choice is None: return

    selected = configs[choice - 1]
    
    try:
        with db_manager as session:
            rows = session.query(GridRow).filter(GridRow.config_id == selected.id).order_by(GridRow.id).all()
        if not rows: print("\n❌ 无详情数据。")
        else:
            clear()
            print(f"策略详情 ID: {selected.id} | 名称: {selected.name}")
            print_structured_grid_result([r.to_dict() for r in rows])
    except Exception as e:
        print(f"\n出错: {e}")
    input("\n按任意键返回...")

def handle_delete_strategy():
    """删除策略"""
    db_manager = DBSessionManager()
    try:
        with db_manager as session:
            configs = session.query(GridConfig).order_by(GridConfig.id).all()
    except Exception as e:
        print(f"出错: {e}"); input("..."); return

    def display(cfg): return f"ID: {cfg.id} | {cfg.name or '无名称'}"

    clear()
    print("【删除策略】")
    display_list_with_index(configs, display)

    choice = get_index_input(len(configs))
    if choice == 'b' or choice is None: return

    selected = configs[choice - 1]
    if confirm_action(f"⚠️ 确定删除 ID {selected.id} ({selected.name}) 及其所有数据吗？"):
        mgr = DBSessionManager()
        if mgr.delete_strategy_by_id(selected.id): print("✅ 删除成功")
        else: print("❌ 删除失败")
        mgr.close()
    input("\n按任意键返回...")

# --- 核心修改：数据导入 ---
def handle_import_market_data():
    """导入行情数据 (手动选择格式)"""
    clear()
    print("【网格交易神器】>【回测数据管理】>【导入行情数据】\n")
    
    # 1. 选择数据源格式
    print("请选择文件数据源格式：\n")
    print("")
    formats = [
        ("Wind 导出 Excel (.xlsx)", "wind"),
        ("iShares ETF 历史数据 Excel (.xlsx) \n[ ⚠️ iShares 如果是 .xls 文件，可能会因为格式问题需要另存为 .xlsx ]", "ishare_excel"),
        ("中证指数官网历史数据 Excel (.xlsx)", "csi_excel"),
        ("Nasdaq 100 历史数据 CSV", "nasdaq_csv"),
        ("比特币历史数据 TSV", "bitcoin_tsv"),
    ]
    
    for i, (desc, _) in enumerate(formats):
        print(f"{i+1}. {desc}")
        
    choice_idx = get_index_input(len(formats))
    if choice_idx == 'b': return
    
    selected_desc, source_type = formats[choice_idx - 1]
    
    # 2. 输入路径
    print(f"\n已选择格式: {selected_desc}")
    file_path_raw = input("请粘贴文件绝对路径 (按 b 取消): ").strip()
    if not file_path_raw or file_path_raw.lower() == 'b': return
    
    file_path = file_path_raw.strip('"').strip("'")
    if not os.path.exists(file_path):
        print(f"\n❌ 文件不存在: {file_path}"); input("按任意键返回..."); return

    print(f"\n正在使用 [{selected_desc}] 加载器导入...")
    
    importer = DataImporter(SQLALCHEMY_DATABASE_URI)
    try:
        # 修改：传入 source_type
        success = importer.import_market_data(file_path, source_type)
        if not success:
            print("\n❌ 导入失败，请检查文件内容是否符合格式要求。")
    except Exception as e:
        print(f"\n❌ 发生严重错误: {e}")
    finally:
        importer.close()
    
    input("\n按任意键返回...")

def handle_view_market_data():
    """查看数据"""
    db_manager = DBSessionManager()
    while True:
        try:
            with db_manager as session:
                 files = session.query(ImportedFiles).order_by(ImportedFiles.id).all()
        except Exception as e:
            print(f"出错: {e}"); input("..."); return

        def display(f): return f"ID: {f.id:<4} | 文件: {f.file_name:<20} | Code: {f.index_code} | 记录: {f.record_count}"

        clear()
        print("【查看数据】\n")
        display_list_with_index(files, display)

        choice = get_index_input(len(files))
        if choice == 'b' or choice is None: return

        sel_file = files[choice - 1]
        try:
             with db_manager as session:
                 records = session.query(IndexData).filter(IndexData.import_id == sel_file.id).order_by(IndexData.date).all()
        except Exception as e:
             print(f"出错: {e}"); input("..."); continue

        # 预览
        clear()
        print(f"文件: {sel_file.file_name} (共 {len(records)} 条，最多展示 300 条）")
        headers = ["日期", "开盘", "最高", "最低", "收盘", "涨跌幅(%)"]
        data = []
        preview = records[:150] + records[-150:] if len(records) > 300 else records
        for r in preview:
            data.append([r.date, r.open_price, r.high_price, r.low_price, r.close_price, r.change_percent])
        print(tabulate(data, headers=headers, floatfmt=".2f"))
        input("\n按任意键返回...")

def handle_delete_market_data():
    """删除数据"""
    db_manager = DBSessionManager()
    try:
        with db_manager as session:
            files = session.query(ImportedFiles).order_by(ImportedFiles.id).all()
    except: return

    def display(f): return f"ID: {f.id} | {f.file_name}"
    
    clear()
    print("【删除数据】")
    display_list_with_index(files, display)
    
    choice = get_index_input(len(files))
    if choice == 'b' or choice is None: return
    
    sel = files[choice - 1]
    if confirm_action(f"⚠️ 确定删除 ID {sel.id} 及其所有数据吗？"):
        mgr = DBSessionManager()
        if mgr.delete_import_batch(sel.id): print("✅ 删除成功")
        else: print("❌ 删除失败")
        mgr.close()
    input("...")

# --- 核心修改：参数推荐 ---
def handle_get_best_params():
    """参数优选"""
    db_manager = DBSessionManager()
    
    # 1. 选择数据
    clear()
    print("【参数推荐】\n[1/4] 选择参考行情\n")
    imported_files = []
    try:
        with db_manager as session:
            imported_files = session.query(ImportedFiles).order_by(ImportedFiles.id).all()
    except Exception as e:
        print(f"数据库错误: {e}"); input("..."); return

    def fmt_file(f): return f"ID:{f.id:<3} | {f.file_name:<20} | {f.date_range}"
    if not display_list_with_index(imported_files, fmt_file): 
        input("无数据，请先导入..."); return

    choice = get_index_input(len(imported_files))
    if choice == 'b' or choice is None: return
    selected_import = imported_files[choice - 1]

    # 2. 输入资金
    clear()
    print("【参数推荐】\n[2/4] 设置\n")
    print(f"已选数据: {selected_import.file_name}")
    capital = input_with_cancel("请输入预计投入资金 (例如 100000): ", float, min_value=1000)
    if capital == 'b': return

    # 3. 选择算法
    print("\n请选择优化算法:")
    print("1. 贝叶斯优化 (Bayesian Optimization) - 推荐")
    print("2. 遗传算法 (Genetic Algorithm) - 开发中")
    algo = input_with_cancel("\n输入选项 (默认1): ", str)
    if algo == 'b': return
    
    algo_key = 'bayes' # 默认为 bayes
    if algo == '2':
        print("⚠️ 遗传算法暂未支持，请等待后续更新。")
        input("..."); return
    elif algo != '1' and algo != '':
        print("⚠️ 选项无效，默认使用贝叶斯。")
        time.sleep(1)

    # 4. 执行优化
    print(f"\n🚀 正在启动优化引擎 (资金: {capital:,.0f})...")
    print("这可能需要几十秒，请稍候...")
    
    try:
        # 获取详细数据
        with db_manager as session:
            data_objs = session.query(IndexData).filter(IndexData.import_id == selected_import.id).order_by(IndexData.date).all()
            # 转为字典列表
            market_data = [d.to_dict() for d in data_objs]
        
        if not market_data:
            print("❌ 数据集为空，无法优化。"); input("..."); return

        # 调用工厂函数
        optimizer = get_optimizer(algo_key, market_data, capital)
        best_params = optimizer.run(n_iter=25)
        
        if not best_params:
            print("❌ 优化失败。"); input("..."); return

        # 5. 显示结果
        clear()
        print("【优化结果报告】\n")
        print(f"⭐ 推荐参数 (预估 XIRR: {best_params['xirr_score']*100:.2f}%)")
        print("-" * 40)
        print(f"波动参数 a: {best_params['a']:.4f}")
        print(f"利润参数 b: {best_params['b']:.4f}")
        print(f"首行触发价: {best_params['first_trigger_price']:.4f}")
        print(f"网格行数  : {best_params['total_rows']}")
        print(f"每行金额  : {best_params['buy_amount']:.2f}")
        print("-" * 40)

        # 6. 保存为策略
        if confirm_action("\n是否将此推荐参数保存为新策略？"):
            name = input_with_cancel("请输入新策略名称: ", str)
            if name != 'b':
                best_params['name'] = name
                # 清理非配置字段
                if 'xirr_score' in best_params: del best_params['xirr_score']
                
                # 生成完整模型并保存
                full_model = generate_grid_from_input(best_params)
                if save_grid_to_db(full_model):
                    print("✅ 策略保存成功！")
                else:
                    print("❌ 保存失败。")

    except Exception as e:
        print(f"\n⚠️ 运行时错误: {e}")
        import traceback; traceback.print_exc()
        
    input("\n按任意键返回...")

def handle_backtest():
    """回测逻辑 (原有保持不变，略微精简)"""
    clear()
    print("【开始回测】\n")
    db_manager = DBSessionManager()

    # 1. 选策略
    try:
        with db_manager as session: configs = session.query(GridConfig).all()
    except: return
    if not configs: print("无策略"); input("..."); return

    def d_cfg(c): return f"ID:{c.id} | {c.name}"
    display_list_with_index(configs, d_cfg)
    c_choice = get_index_input(len(configs))
    if c_choice == 'b' or c_choice is None: return
    sel_conf = configs[c_choice - 1]

    # 获取策略行
    try:
        with db_manager as session:
            rows = session.query(GridRow).filter(GridRow.config_id == sel_conf.id).order_by(GridRow.id).all()
            grid_strategy = [r.to_dict() for r in rows]
    except: return

    # 2. 选数据
    try:
        with db_manager as session: files = session.query(ImportedFiles).all()
    except: return
    if not files: print("无数据"); input("..."); return

    def d_file(f): return f"ID:{f.id} | {f.file_name}"
    clear(); print(f"已选策略: {sel_conf.name}\n[2/3] 选数据")
    display_list_with_index(files, d_file)
    f_choice = get_index_input(len(files))
    if f_choice == 'b' or f_choice is None: return
    sel_file = files[f_choice - 1]

    try:
        with db_manager as session:
            data = session.query(IndexData).filter(IndexData.import_id == sel_file.id).order_by(IndexData.date).all()
            grid_data = [d.to_dict() for d in data]
    except: return

    # 3. 资金
    clear(); print("[3/3] 资金")
    default_cash = sel_conf.total_rows * sel_conf.buy_amount
    capital = input_with_cancel(f"输入资金 (默认 {default_cash:,.0f}): ", float)
    if capital == 'b': return
    if not capital: capital = default_cash

    # 4. 跑
    clear(); print("回测中...")
    try:
        bt = BackTest(grid_data, grid_strategy, capital)
        res = bt.run_backtest()
        
        metrics = res['metrics']
        print("-" * 30)
        print(f"最终资金: {metrics['final_net_value']:,.2f}")
        print(f"收益率  : {metrics['simple_return']:.2%}")
        print(f"XIRR    : {metrics['xirr']*100:.2f}%")
        print("-" * 30)
        
        # 保存 Excel (简化版逻辑)
        if confirm_action("保存结果到 Excel?"):
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = f"reports/Backtest_{ts}.xlsx"
            os.makedirs("reports", exist_ok=True)
            with pd.ExcelWriter(path) as writer:
                pd.DataFrame([metrics]).to_excel(writer, sheet_name="Metrics")
                res['df_trades'].to_excel(writer, sheet_name="Trades")
            print(f"已保存: {path}")

    except Exception as e:
        print(f"回测错: {e}")
    input("...")

if __name__ == "__main__":
    run_cli()