# service/cli.py
import os
import time
import sys
# 移除了 tkinter 和 filedialog 的导入
from typing import List, Dict, Any, Optional
from tabulate import tabulate
import traceback # 用于打印详细错误
from datetime import datetime
import pandas as pd

# 假设你的项目结构能正确导入这些模块
try:
    # 从 dao 包导入
    from dao.grid_data_structure import GridConfig, GridRow, ImportedFiles, IndexData # 导入所有需要的模型
    from dao.db_function_library import DBSessionManager, init_db
    from dao.data_importer import DataImporter
    from dao.config import SQLALCHEMY_DATABASE_URI

    # 从 util 包导入
    from util.build_grid_model import generate_grid_from_input, print_structured_grid_result, save_grid_to_db
    from util.init_to_json import excel_to_json # 导入 Excel 转 Json 函数
    from util.backtest import BackTest # 导入 BackTest

except ImportError as e:
    print(f"启动时导入模块失败: {e}")
    print("请确保在项目根目录运行，并且 Conda 环境已激活且安装了所有依赖。")
    input("按回车键退出...") # 阻塞退出，让用户看到错误
    sys.exit(1)

# --- 辅助函数 ---
def clear():
    """清屏函数"""
    os.system('cls' if os.name == 'nt' else 'clear')

# 修改：移除 header 参数
def display_list_with_index(items: list, display_func=None, show_empty_message=True):
    """显示带序号的列表，返回列表是否为空 (不打印标题)"""
    # clear() # 清屏移到调用处
    # print(header) # 标题移到调用处
    # print('\n')
    if not items:
        if show_empty_message:
            print("\n列表为空。")
        # print("\nb. 返回上一菜单")
        return False # 列表为空

    if display_func:
        for i, item in enumerate(items):
            print(f"{i+1}. {display_func(item)}")
    else:
        for i, item in enumerate(items):
            print(f"{i+1}. {item}")

    # print("\nb. 返回上一菜单")
    return True # 列表非空

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
    # 确保 init_db 在 db_function_library.py 中已修正
    if init_db() is None:
        print("数据库初始化检查失败，无法启动程序。")
        input("按回车键退出...")
        return

    main_menu = {
        '1': ('策略管理', handle_strategy_management),
        '2': ('回测数据管理', handle_data_management),
        '3': ('开始回测', handle_backtest),
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
                    # traceback.print_exc() # 调试时用
                    input("\n按任意键返回主菜单...")
            # else: pass # 'c'
        else:
            print("\n❌ 无效选项，请重新输入！")
            time.sleep(0.5)

def handle_strategy_management():
    """处理策略管理子菜单"""
    strategy_menu = {
        '1': ('新建策略', handle_create_strategy),
        '2': ('查看已有策略', handle_view_strategies),
        '3': ('删除策略', handle_delete_strategy),
        # 'b': ('返回主菜单', None)
    }
    while True:
        clear()
        print("【网格交易神器】>【策略管理】\n")
        # print("（按 b 返回）\n")
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
                    # traceback.print_exc()
                    input("\n按任意键返回策略管理菜单...")
            # else: pass # 'b'
        else:
            print("\n❌ 无效选项，请重新输入！")
            time.sleep(0.5)

def handle_data_management():
    """处理回测数据管理子菜单"""
    data_menu = {
        '1': ('导入行情数据 (.xlsx)', handle_import_market_data),
        '2': ('查看现有数据', handle_view_market_data),
        '3': ('删除行情数据 (按导入批次)', handle_delete_market_data),
        # 'b': ('返回主菜单', None)
    }
    while True:
        clear()
        print("【网格交易神器】>【回测数据管理】\n")
        # print("（按 b 返回）\n")
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
                    # traceback.print_exc()
                    input("\n按任意键返回数据管理菜单...")
            # else: pass # 'b'
        else:
            print("\n❌ 无效选项，请重新输入！")
            time.sleep(0.5)

# --- 具体功能实现 ---

def handle_create_strategy():
    """处理新建策略的逻辑"""
    clear()
    print("【网格交易神器】>【策略管理】>【新建策略】")
    print("（按 b 取消）\n")
    params = {}
    prompts = [
        ("name", "[1/6] 请输入策略名称（可选）: ", str, None, None),
        ("a", "[2/6] 请输入波动捕捉大小参数 a (0.05~0.30): ", float, 0.05, 0.30),
        ("b", "[3/6] 请输入每行收益率参数 b (0.05~0.30): ", float, 0.05, 0.30),
        ("first_trigger_price", "[4/6] 请输入首个触发价 (例如 1.000): ", float, 0.0001, None),
        ("total_rows", "[5/6] 请输入总行数 (例如 5): ", int, 1, None),
        ("buy_amount", "[6/6] 请输入每次买入金额 (例如 10000.0): ", float, 0.01, None)
    ]

    for key, prompt, type, min_val, max_val in prompts:
        value = input_with_cancel(prompt, type, min_val, max_val)
        if value == 'b': print("\n操作已取消。"); time.sleep(0.5); return
        if key == "name":
            if isinstance(value, str) and value.lower() == 'b':
                 print("⚠️ 策略名称不能是 'b'。"); print("\n操作已取消。"); time.sleep(0.5); return
            params[key] = value if value else None
        else: params[key] = value

    try:
        result = generate_grid_from_input(params)
        print("\n--- 生成的策略数据预览 ---")
        print_structured_grid_result(result["rows"]) # 依赖此函数正确打印

        if confirm_action("\n是否保存该策略？"):
            if save_grid_to_db(result): print("✅ 策略已保存到数据库！")
            else: print("❌ 保存策略失败。") 
        else: print("👌 策略不保存。")
    except Exception as e:
         print(f"\n⚠️ 生成或保存策略时出错: {e}")
         # traceback.print_exc()
    input("\n按任意键返回策略管理菜单...")


def handle_view_strategies():
    """处理查看已有策略的逻辑"""
    db_manager = DBSessionManager()
    try:
        with db_manager as session:
            configs = session.query(GridConfig).order_by(GridConfig.id).all()
    except Exception as e:
        print(f"查询策略列表时出错: {e}"); input("\n按任意键返回..."); return

    def display_config(cfg: GridConfig):
        last_modified_str = cfg.last_modified.strftime("%Y-%m-%d %H:%M") if cfg.last_modified else "无"
        name_str = cfg.name if cfg.name else "无名称"
        return f"ID: {cfg.id:<4} | 名称: {name_str:<15} | a={cfg.a:<4.2f} | b={cfg.b:<4.2f} | 行数: {cfg.total_rows:<3} | 修改: {last_modified_str}"

    clear()
    print("【网格交易神器】>【策略管理】>【查看已有策略】\n")
    # print("（按 b 返回）\n")
    list_not_empty = display_list_with_index(configs, display_config, show_empty_message=True)

    choice = get_index_input(len(configs))
    if choice == 'b' or choice is None: return

    selected_config = configs[choice - 1]
    choice_id = selected_config.id

    try:
        with db_manager as session:
            rows = session.query(GridRow).filter(GridRow.config_id == choice_id).order_by(GridRow.id).all()
    except Exception as e:
        print(f"\n查询策略详情时出错: {e}"); input("\n按任意键返回..."); return

    if not rows: print(f"\n❌ 未找到策略 ID {choice_id} 的详细行数据。")
    else:
        clear()
        print(f"【网格交易神器】>【策略管理】>【查看已有策略】> 策略 ID: {choice_id}\n")
        print(f"名称: {selected_config.name or '无名称'}")
        print(f"参数: a={selected_config.a}, b={selected_config.b}, 首触价={selected_config.first_trigger_price}, 行数={selected_config.total_rows}, 每行金额={selected_config.buy_amount}")
        # print("-" * 30)
        try:
            dict_rows = [row.to_dict() for row in rows]
            print_structured_grid_result(dict_rows) # 依赖此函数打印表格
        except Exception as e:
            print(f"\n格式化或打印策略详情时出错: {e}")
    input("\n按任意键返回列表...")

def handle_delete_strategy():
    """处理删除策略的逻辑"""
    db_manager = DBSessionManager() # 用于查询列表
    configs = []
    try:
        with db_manager as session:
            configs = session.query(GridConfig).order_by(GridConfig.id).all()
    except Exception as e:
        print(f"查询策略列表时出错: {e}")
        input("\n按任意键返回...")
        return

    # 复用查看策略时的显示函数
    def display_config_for_delete(cfg: GridConfig):
        last_modified_str = cfg.last_modified.strftime("%Y-%m-%d %H:%M") if cfg.last_modified else "无"
        name_str = cfg.name if cfg.name else "无名称"
        return f"ID: {cfg.id:<4} | 名称: {name_str:<15} | a={cfg.a:<4.2f} | b={cfg.b:<4.2f} | 行数: {cfg.total_rows:<3} | 修改: {last_modified_str}"

    # 手动打印标题
    clear()
    print("【网格交易神器】>【策略管理】>【删除策略】")
    list_not_empty = display_list_with_index(configs, display_config_for_delete, show_empty_message=True)

    choice = get_index_input(len(configs))
    if choice == 'b' or choice is None: return # 返回

    selected_config = configs[choice - 1]
    config_id_to_delete = selected_config.id
    strategy_name = selected_config.name or f"ID {config_id_to_delete}"

    # 再次确认删除
    prompt = (f"⚠️ 警告：确定要删除策略 '{strategy_name}' (ID: {config_id_to_delete}) 吗？\n"
              f"   所有相关的网格行数据 ({selected_config.total_rows} 行) 也将被永久删除且无法恢复！")

    if confirm_action(prompt):
        print(f"\n正在删除策略 ID: {config_id_to_delete}...")
        delete_success = False
        # 使用新的 DBSessionManager 实例来执行删除操作
        delete_manager = DBSessionManager()
        try:
            # 调用新添加的数据库删除方法
            delete_success = delete_manager.delete_strategy_by_id(config_id_to_delete)
            if not delete_success:
                print("删除操作失败。") # delete_strategy_by_id 内部会打印详细错误
        except Exception as e:
            print(f"执行删除时发生意外错误: {e}")
            # traceback.print_exc()
        finally:
            delete_manager.close() # 关闭 session
    else:
        print("操作已取消。")

    input("\n按任意键返回...")

def handle_import_market_data():
    """处理导入行情数据的逻辑 (改为粘贴路径)"""
    clear()
    print("【网格交易神器】>【回测数据管理】>【导入行情数据】\n")
    # print("（按 b 返回）\n")
    print("请确保行情 Excel 文件第一行为表头，且包含以下列名:\n")
    print("- 日期Date (格式: YYYYMMDD 整数)")
    print("- 指数代码Index Code")
    print("- 开盘Open, 最高High, 最低Low, 收盘Close")
    print("- 涨跌幅(%)Change(%)")

    excel_file_path_raw = input("\n请粘贴 Excel 文件的绝对路径 (按 b 取消): ").strip()
    if not excel_file_path_raw or excel_file_path_raw.lower() == 'b':
        print("\n操作已取消。"); time.sleep(0.5); return
    
    excel_file_path = excel_file_path_raw.strip('"').strip("'")

    if not os.path.exists(excel_file_path):
        print(f"\n❌ 文件路径不存在或无效: {excel_file_path}"); input("\n按任意键返回..."); return
    if not (excel_file_path.lower().endswith(".xlsx") or excel_file_path.lower().endswith(".xls")):
         print(f"\n❌ 文件似乎不是 Excel 文件 (.xlsx 或 .xls): {excel_file_path}"); input("\n按任意键返回..."); return

    print(f"\n已选择文件: {excel_file_path}")
    original_filename = os.path.basename(excel_file_path)
    data_folder = os.path.join("data", "database_folder")
    os.makedirs(data_folder, exist_ok=True)
    json_file_path = os.path.join(data_folder, f"{os.path.splitext(original_filename)[0]}_temp_import.json")

    print("\n1. 正在将 Excel 转换为 JSON...")
    convert_success = False
    try:
        convert_success = excel_to_json(excel_file_path, json_file_path) # 依赖此函数
        if convert_success: print(f"✅ JSON 文件已生成: {json_file_path}")
        else: print("❌ Excel 转 JSON 失败。")
    except Exception as e:
        print(f"❌ Excel 转 JSON 时发生错误: {e}")

    if not convert_success: input("\n按任意键返回..."); return

    print("\n2. 正在将 JSON 数据导入数据库...")
    importer = None
    import_success = False
    try:
        importer = DataImporter(SQLALCHEMY_DATABASE_URI)
        import_success = importer.import_market_data_from_json(json_file_path, original_filename)
        if not import_success: print("❌ 数据导入数据库失败。")
    except Exception as e:
        print(f"❌ 数据导入时发生严重错误: {e}")
    finally:
        if importer: importer.close()
        if os.path.exists(json_file_path):
            try: os.remove(json_file_path)
            except Exception as e_clean: print(f"警告：清理临时 JSON 文件失败: {e_clean}")
    input("\n按任意键返回...")


def handle_view_market_data():
    """查看现有数据 - 简化版，不分页，返回列表"""
    db_manager = DBSessionManager()
    while True: # 外层循环
        try:
            # 使用上下文管理器确保 session 关闭
            with db_manager as session:
                 # imported_files = db_manager.get_all_imported_files() # 如果方法需要 session
                 # 如果不需要 session，可以直接调用
                 imported_files = session.query(ImportedFiles).order_by(ImportedFiles.id).all() # 直接查询
        except Exception as e:
            print(f"查询导入列表时出错: {e}"); input("\n按任意键返回..."); return

        def display_import_info(f: ImportedFiles):
             return f"ID: {f.id:<4} | 文件: {f.file_name or 'N/A':<25} | Code: {f.index_code:<8} | 记录: {f.record_count or 'N/A':<5} | 日期: {f.date_range or 'N/A'}"

        # 手动打印标题
        clear()
        print("【网格交易神器】>【回测数据管理】>【查看现有数据】\n")
        # print("（按 b 返回）\n")
        list_not_empty = display_list_with_index(imported_files, display_import_info, show_empty_message=True)

        choice = get_index_input(len(imported_files))
        if choice == 'b' or choice is None: return # 返回上级菜单

        selected_import_record = imported_files[choice - 1]
        selected_import_id = selected_import_record.id

        try:
             with db_manager as session:
                 records = session.query(IndexData).filter(IndexData.import_id == selected_import_id).order_by(IndexData.date).all()
        except Exception as e:
             print(f"查询 Import ID {selected_import_id} 数据时出错: {e}")
             input("\n按任意键返回列表..."); continue # 返回列表

        # 显示预览
        clear()
        print(f"【网格交易神器】> ... >【查看现有数据】> Import ID: {selected_import_id}\n")
        print(f"文件: {selected_import_record.file_name or 'N/A'}")
        if not records: print("\n未找到相关行情数据。")
        else:
             total_records = len(records)
             print(f"共 {total_records} 条记录。")
             print(f"Index Code: {records[0].index_code}")
             date_range_str = selected_import_record.date_range or f"{records[0].date.strftime('%Y-%m-%d')} ~ {records[-1].date.strftime('%Y-%m-%d')}"
             print(f"日期范围: {date_range_str}")

             preview_count = 5
             display_records = records[:preview_count] + records[-preview_count:] if total_records > 2 * preview_count else records
             headers = ["原始行号", "日期", "开盘", "最高", "最低", "收盘", "涨跌幅(%)"]
             display_data = []
             for i, r in enumerate(display_records):
                 original_index = records.index(r) + 1
                 display_data.append([
                     original_index, r.date.strftime('%Y-%m-%d'), r.open_price, r.high_price,
                     r.low_price, r.close_price, r.change_percent
                 ])
             print("\n--- 数据预览 (部分数据) ---")
             print(tabulate(display_data, headers=headers, tablefmt="psql", floatfmt=".3f")) # 使用 psql 格式
             if total_records > 2 * preview_count: print(f"... (共 {total_records} 条) ...")
        input("\n按任意键返回列表...")


def handle_delete_market_data():
    """处理删除行情数据（按导入批次）的逻辑"""
    db_manager = DBSessionManager() # 用于查询列表
    imported_files = [] # 初始化
    try:
        with db_manager as session:
            imported_files = session.query(ImportedFiles).order_by(ImportedFiles.id).all()
    except Exception as e:
        print(f"查询导入列表时出错: {e}"); input("\n按任意键返回..."); return

    def display_import_info_for_delete(f: ImportedFiles):
         return f"ID: {f.id:<4} | 文件: {f.file_name or 'N/A':<25} | Code: {f.index_code:<8} | 记录: {f.record_count or 'N/A':<5}"

    # 手动打印标题
    clear()
    print("【网格交易神器】>【回测数据管理】>【删除行情数据】\n")
    # print("（按 b 返回）\n")
    list_not_empty = display_list_with_index(imported_files, display_import_info_for_delete, show_empty_message=True)

    choice = get_index_input(len(imported_files))
    if choice == 'b' or choice is None: return

    selected_import_record = imported_files[choice - 1]
    selected_import_id = selected_import_record.id

    prompt = (f"⚠️ 警告：确定要删除导入批次 ID {selected_import_id} "
              f"(文件: {selected_import_record.file_name or 'N/A'}, Code: {selected_import_record.index_code}) "
              f"及其所有关联的行情数据吗？此操作无法恢复！")

    if confirm_action(prompt):
        print("\n正在执行删除操作...")
        delete_success = False
        # 使用新的 db_manager 实例执行删除，确保事务独立
        delete_manager = DBSessionManager()
        try:
             # 确保 delete_import_batch 在 db_function_library.py 中已修正
             delete_success = delete_manager.delete_import_batch(selected_import_id)
             if not delete_success: print("删除操作失败。") # 假设内部打印错误
        except Exception as e:
             print(f"执行删除时发生意外错误: {e}")
             # traceback.print_exc()
        # finally:
        #      delete_manager.close() # 关闭新实例的 session
    else:
        print("操作已取消。")
    input("\n按任意键返回...")


def handle_backtest():
    """处理开始回测的逻辑"""
    clear()
    print("【网格交易神器】>【开始回测】\n")
    db_manager = DBSessionManager()

    # --- 步骤 1: 选择策略 ---
    configs = []
    try:
        with db_manager as session:
            configs = session.query(GridConfig).order_by(GridConfig.id).all()
    except Exception as e:
        print(f"查询策略列表时出错: {e}"); input("\n按任意键返回..."); return

    def display_config_for_backtest(cfg):
        name_str = cfg.name if cfg.name else "无名称"
        return f"ID: {cfg.id:<4} | 名称: {name_str:<15} | a={cfg.a:<4.2f} | b={cfg.b:<4.2f} | 行数: {cfg.total_rows:<3}"

    clear()
    print("【网格交易神器】>【开始回测】\n[1/3] 选择策略\n")
    list_not_empty_step1 = display_list_with_index(configs, display_config_for_backtest, show_empty_message=False)
    if not list_not_empty_step1: print("\n没有可用的策略。"); input("\n按任意键返回..."); return

    strategy_choice = get_index_input(len(configs))
    if strategy_choice == 'b' or strategy_choice is None: return
    selected_config = configs[strategy_choice - 1]
    strategy_id = selected_config.id

    grid_strategy = []
    try:
        with db_manager as session:
            grid_rows = session.query(GridRow).filter(GridRow.config_id == strategy_id).order_by(GridRow.id).all()
        if not grid_rows: print(f"\n❌ 策略 {strategy_id} 详情未找到。"); input("\n按任意键返回..."); return
        grid_strategy = [row.to_dict() for row in grid_rows]
    except Exception as e:
        print(f"\n查询策略详情时出错: {e}"); input("\n按任意键返回..."); return

    # --- 步骤 2: 选择数据 ---
    imported_files = []
    try:
        with db_manager as session:
            imported_files = session.query(ImportedFiles).order_by(ImportedFiles.id).all()
    except Exception as e:
        print(f"\n查询数据批次列表时出错: {e}"); input("\n按任意键返回..."); return

    def display_import_info_for_backtest(f: ImportedFiles):
         return f"ID: {f.id:<4} | 文件: {f.file_name or 'N/A':<25} | Code: {f.index_code:<8} | 日期: {f.date_range or 'N/A'}"

    clear()
    print("【网格交易神器】>【开始回测】\n[2/3] 选择数据批次\n")
    list_not_empty_step2 = display_list_with_index(imported_files, display_import_info_for_backtest, show_empty_message=False)
    if not list_not_empty_step2: print("\n没有可用的回测数据。"); input("\n按任意键返回..."); return

    data_choice = get_index_input(len(imported_files))
    if data_choice == 'b' or data_choice is None: return
    selected_import_record = imported_files[data_choice - 1]
    selected_import_id = selected_import_record.id

    grid_data = []
    try:
        with db_manager as session:
            grid_data_list = session.query(IndexData).filter(IndexData.import_id == selected_import_id).order_by(IndexData.date).all()
        if not grid_data_list: print(f"\n❌ 未找到 Import ID {selected_import_id} 的行情数据。"); input("\n按任意键返回..."); return
        grid_data = [row.to_dict() for row in grid_data_list]
    except Exception as e:
        print(f"\n加载行情数据时出错: {e}"); input("\n按任意键返回..."); return
    
    # --- 步骤 3: 输入初始资金 ---
    clear()
    print("【网格交易神器】>【开始回测】\n[3/3] 输入初始资金（默认：表格每行占用资金之和）\n")

    initial_capital = input_with_cancel(f"请输入初始资金 (回车选择 {selected_config.total_rows * selected_config.buy_amount:,.2f} 。按 b 取消): ", str)
    if initial_capital == 'b':
        return
    elif not initial_capital:
        initial_capital = None # 使用默认值
    else:
        try:
            initial_capital = float(initial_capital)
            if initial_capital <= 0:
                print("❌ 初始资金必须为正数。")
                input("\n按任意键返回...")
                return
        except ValueError:
            print("❌ 无效的初始资金输入。")
            input("\n按任意键返回...")
            return

    # --- 执行回测 ---
    clear()
    print(f"--- 正在开始回测 ---")
    print(f"策略: {selected_config.name or '无名称'} (ID: {strategy_id})")
    print(f"数据: {selected_import_record.file_name or 'N/A'} (ID: {selected_import_id}, Code: {selected_import_record.index_code})")
    print("-" * 40 + "\n")
    try:
        backtest = BackTest(grid_data, grid_strategy, initial_capital) # 假设 BackTest 接受字典列表
        result = backtest.run_backtest() # 假设内部打印流水/快照
        df_trades = result.get("df_trades") if result else pd.DataFrame()
        df_daily = result.get("df_daily") if result else pd.DataFrame()
        # 确保即使键存在但值为 None 时也是 DataFrame
        if df_trades is None: df_trades = pd.DataFrame()
        if df_daily is None: df_daily = pd.DataFrame()

        print("\n" + "-" * 40)
        print("--- 回测指标总结 ---")
        metrics = result.get("metrics", {})
        print(f"{'初始资金':<15}: {metrics.get('initial_capital', 0):,.2f}")
        print(f"{'最终资金':<15}: {metrics.get('final_net_value', 0):,.2f}")

        def format_metric(value, format_str):
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                try: return format(value, format_str)
                except (ValueError, TypeError): return str(value)
            elif value is None: return 'N/A'
            else: return str(value)
        print(f"{'最大占用资金':<15}: {format_metric(metrics.get('max_cash_used'), ',.2f')}")
        print(f"{'触发表格买入行数':<15}: {format_metric(metrics.get('triggered_rows'), 'd')}")
        print(f"{'买入次数':<15}: {format_metric(metrics.get('buy_num'), 'd')}")
        print(f"{'买入失败次数':<15}: {format_metric(metrics.get('buy_fail_num'), 'd')}")
        print(f"{'卖出次数':<15}: {format_metric(metrics.get('sell_num'), 'd')}")
        print(f"{'策略 XIRR':<15}: {format_metric(metrics.get('xirr')*100, '.2f')}%")
        print(f"{'简单收益率':<15}: {format_metric(metrics.get('simple_return'), '.2%')}")
        print(f"{'最大回撤 (相对峰值)':<18}: {format_metric(metrics.get('max_drawdown_peak'), '.2%')}")
        print(f"{'⬆️计算公式':<15}: {'MIN(峰值后的净值谷值 - 净值峰值) / 净值峰值 *100%'}")
        print(f"{'最大回撤 (相对初始)':<18}: {format_metric(metrics.get('max_drawdown_initial'), '.2%')}")
        print(f"{'⬆️计算公式':<15}: {'MIN(净值谷值 - 初始资金) / 初始资金 *100%'}")
        print(f"{'年化夏普比':<15}: {format_metric(metrics.get('sharpe'), '.2f')}")
        print(f"{'年化波动率':<15}: {format_metric(metrics.get('volatility'), '.2%')}")
        print("-" * 40)

    # --- 3. 新增：保存结果到 Excel ---
        if result: # 确保回测成功执行了
            print("\n正在保存回测结果到 Excel 文件...")
            # 3.1 创建结果目录
            results_dir = "reports"
            os.makedirs(results_dir, exist_ok=True)

            # 3.2 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            strategy_name_part = selected_config.name if selected_config.name else f"ID{strategy_id}"
            # 替换掉策略名中可能不适合做文件名的字符 (简化处理，只替换空格和冒号)
            strategy_name_part = strategy_name_part.replace(" ", "_").replace(":", "-")
            index_code_part = selected_import_record.index_code
            import_id_part = selected_import_id
            filename = f"回测结果 {timestamp} - {strategy_name_part} {index_code_part} import_id {import_id_part}.xlsx"
            filepath = os.path.join(results_dir, filename)

            # 3.3 准备数据
            # 指标数据
            metrics_df = pd.DataFrame(list(metrics.items()), columns=['指标 (Metric)', '值 (Value)'])
            # 策略配置数据
            config_dict = selected_config.to_dict() # 假设模型有 to_dict 方法
            # 移除 'rows' 关联，避免写入 Excel
            if 'rows' in config_dict: del config_dict['rows']
            if 'last_modified' in config_dict and isinstance(config_dict['last_modified'], datetime):
                 config_dict['last_modified'] = config_dict['last_modified'].strftime("%Y-%m-%d %H:%M:%S")

            config_df = pd.DataFrame([config_dict]) # 单行 DataFrame
            # 策略行数据 (grid_strategy 是 List[Dict])
            strategy_rows_df = pd.DataFrame(grid_strategy)

            # 3.4 写入 Excel
            try:
                with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                    metrics_df.to_excel(writer, sheet_name='指标总览 (Metrics)', index=False)
                    df_daily.to_excel(writer, sheet_name='每日快照 (Daily)', index=False)
                    df_trades.to_excel(writer, sheet_name='交易流水 (Trades)', index=False)
                    # 将策略配置和行写入同一 Sheet，配置在上，行数据在下
                    config_df.to_excel(writer, sheet_name='策略详情 (Strategy)', index=False, startrow=0)
                    # 加一个空行和标题
                    pd.DataFrame([{"---": "---"}] * 2).to_excel(writer, sheet_name='策略详情 (Strategy)', index=False, header=False, startrow=config_df.shape[0] + 1) # 空行
                    pd.DataFrame([{"网格行数据 (Grid Rows)": ""}]).to_excel(writer, sheet_name='策略详情 (Strategy)', index=False, header=True, startrow=config_df.shape[0] + 3) # 标题行
                    strategy_rows_df.to_excel(writer, sheet_name='策略详情 (Strategy)', index=False, startrow=config_df.shape[0] + 4) # 行数据

                print(f"✅ 回测结果已保存至: {filepath}")
            except Exception as e_save:
                print(f"\n❌ 保存 Excel 文件时出错: {e_save}")
        # --- 保存结束 ---
    
    except Exception as e:
        print(f"\n⚠️ 回测过程中发生错误: {e}")
        # traceback.print_exc()
    input("\n按任意键返回主菜单...")

# --- 主程序入口 ---
# if __name__ == "__main__":
#     run_cli()