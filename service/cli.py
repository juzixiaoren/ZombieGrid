# service/cli.py
import os
import time
import sys
import tkinter as tk
from tkinter import filedialog
from typing import List, Dict, Any, Optional # 增加类型提示
from tabulate import tabulate
import traceback # 用于打印详细错误

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


# msvcrt/termios 相关的代码用于 getwch (可选，用于倒计时中断，这里暂时注释掉，如果需要再启用)
# try:
#     import msvcrt
#     WINDOWS = True
#     def getwch_or_none(): # 非阻塞获取字符
#         if msvcrt.kbhit():
#             return msvcrt.getwch()
#         return None
# except ImportError:
#     import select
#     import tty
#     import termios
#     WINDOWS = False
#     def getwch_or_none(): # 非阻塞获取字符 (Unix-like)
#         fd = sys.stdin.fileno()
#         old_settings = termios.tcgetattr(fd)
#         try:
#             tty.setraw(sys.stdin.fileno())
#             # 使用 select 实现非阻塞读取
#             if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
#                 ch = sys.stdin.read(1)
#                 return ch
#         finally:
#             termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
#         return None

# --- 辅助函数 ---
def clear():
    """清屏函数"""
    os.system('cls' if os.name == 'nt' else 'clear')

def display_list_with_index(items: list, header: str, display_func=None, show_empty_message=True):
    """显示带序号的列表，返回列表是否为空"""
    clear()
    print(f"=== {header} ===")
    if not items:
        if show_empty_message:
            print("列表为空。")
        return False # 列表为空
    if display_func:
        for i, item in enumerate(items):
            print(f"{i+1}. {display_func(item)}")
    else:
        for i, item in enumerate(items):
            print(f"{i+1}. {item}")
    print("\nb. 返回上一菜单")
    return True # 列表非空

def get_index_input(max_index: int) -> int | str | None:
    """获取用户输入的序号，处理'b'和无效输入"""
    if max_index <= 0:
        return None
    while True:
        choice = input(f"请输入选项序号 (1-{max_index}) 或 'b' 返回: ").strip().lower()
        if choice == 'b':
            return 'b'
        try:
            index_num = int(choice)
            if 1 <= index_num <= max_index:
                return index_num
            else:
                print(f"❌ 无效序号，请输入 1 到 {max_index} 之间的数字。")
        except ValueError:
            print("❌ 无效输入，请输入数字序号或 'b'。")

def confirm_action(prompt: str) -> bool:
    """要求用户确认操作"""
    while True:
        choice = input(f"{prompt} (y/n): ").strip().lower()
        if choice == 'y':
            return True
        elif choice == 'n':
            return False
        else:
            print("请输入 'y' 或 'n'。")

def input_with_cancel(prompt: str, input_type=str, min_value=None, max_value=None):
    """封装输入逻辑，允许输入 'b' 取消"""
    while True:
        value_str = input(prompt).strip()
        if value_str.lower() == 'b':
            return 'b' # 返回特殊标记表示取消
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
                # 对名称 'b' 的限制移到调用处处理
                return value_str
        except ValueError:
            if input_type == float or input_type == int:
                print(f"❌ 请输入一个有效的数字{' (整数)' if input_type == int else ''} 或 'b' 取消。")
            else:
                 print("❌ 无效输入。")

# --- 主菜单和子菜单处理函数 ---
def run_cli():
    """运行命令行界面的主函数"""
    if init_db() is None:
        print("数据库初始化失败，无法启动程序。")
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
        print("=== 网格交易神器 ===")
        for key, (label, _) in main_menu.items():
            print(f"{key}. {label}")

        choice = input("输入选项: ").strip().lower()

        if choice == 'c':
            print("\n👋 再见")
            break

        if choice in main_menu:
            label, action = main_menu[choice]
            if action:
                try:
                    action() # 调用对应的处理函数
                except Exception as e:
                    print(f"\n⚠️ 功能执行时遇到错误: {e}")
                    # traceback.print_exc() # 调试时取消注释以查看详细信息
                    input("\n按任意键返回主菜单...")
            # else: pass # 'c' 选项
        else:
            print("\n❌ 无效选项，请重新输入！")
            time.sleep(1.5)

def handle_strategy_management():
    """处理策略管理子菜单"""
    strategy_menu = {
        '1': ('新建策略', handle_create_strategy),
        '2': ('查看已有策略', handle_view_strategies),
        'b': ('返回主菜单', None)
    }
    while True:
        clear()
        print("=== 策略管理 ===")
        for key, (label, _) in strategy_menu.items():
            print(f"{key}. {label}")

        choice = input("输入选项: ").strip().lower()
        if choice == 'b': break
        if choice in strategy_menu:
            label, action = strategy_menu[choice]
            if action:
                try:
                    action()
                except Exception as e:
                    print(f"\n⚠️ 功能执行时遇到错误: {e}")
                    # traceback.print_exc()
                    input("\n按任意键返回策略管理菜单...")
            # else: pass # 'b' 选项
        else:
            print("\n❌ 无效选项，请重新输入！")
            time.sleep(1.5)

def handle_data_management():
    """处理回测数据管理子菜单"""
    data_menu = {
        '1': ('导入行情数据 (.xlsx)', handle_import_market_data),
        '2': ('查看现有数据', handle_view_market_data),
        '3': ('删除行情数据 (按导入批次)', handle_delete_market_data),
        'b': ('返回主菜单', None)
    }
    while True:
        clear()
        print("=== 回测数据管理 ===")
        for key, (label, _) in data_menu.items():
            print(f"{key}. {label}")

        choice = input("输入选项: ").strip().lower()
        if choice == 'b': break
        if choice in data_menu:
            label, action = data_menu[choice]
            if action:
                try:
                    action()
                except Exception as e:
                    print(f"\n⚠️ 功能执行时遇到错误: {e}")
                    # traceback.print_exc()
                    input("\n按任意键返回数据管理菜单...")
            # else: pass # 'b' 选项
        else:
            print("\n❌ 无效选项，请重新输入！")
            time.sleep(1.5)

# --- 具体功能实现 ---

def handle_create_strategy():
    """处理新建策略的逻辑"""
    clear()
    print("=== 新建策略 ===")
    print("在任何步骤输入 'b' 并回车可取消并返回。")
    params = {}
    prompts = [
        ("name", "请输入策略名称 (可选, 按回车跳过, 不能是 'b'): ", str, None, None),
        ("a", "请输入波动捕捉大小参数 a (0.05~0.30): ", float, 0.05, 0.30),
        ("b", "请输入每行收益率参数 b (0.05~0.30): ", float, 0.05, 0.30),
        ("first_trigger_price", "请输入首个触发价 (例如 1.000): ", float, 0.0001, None),
        ("total_rows", "请输入总行数 (例如 5): ", int, 1, None),
        ("buy_amount", "请输入每次买入金额 (例如 10000.0): ", float, 0.01, None)
    ]

    for key, prompt, type, min_val, max_val in prompts:
        value = input_with_cancel(prompt, type, min_val, max_val)
        if value == 'b':
            print("\n操作已取消。")
            time.sleep(1.5)
            return
        if key == "name":
            # 检查名称是否为 'b' (忽略大小写)
            if isinstance(value, str) and value.lower() == 'b':
                 print("❌ 策略名称不能是 'b'。")
                 print("\n操作已取消。")
                 time.sleep(1.5)
                 return
            params[key] = value if value else None # 空字符串转为 None
        else:
            params[key] = value

    try:
        result = generate_grid_from_input(params)
        print("\n--- 生成的策略数据预览 ---")
        # 假设 print_structured_grid_result 能处理字典列表
        print_structured_grid_result(result["rows"])

        if confirm_action("\n是否保存该策略？"):
             # 假设 save_grid_to_db 能处理字典并返回 bool
            if save_grid_to_db(result):
                print("✅ 策略已保存到数据库！")
            else:
                # save_grid_to_db 内部应该已经打印了错误信息
                print("❌ 保存策略失败。")
        else:
            print("❌ 策略未保存。")

    except Exception as e:
         print(f"\n⚠️ 生成或保存策略时出错: {e}")
         # traceback.print_exc()

    input("\n按任意键返回策略管理菜单...")


def handle_view_strategies():
    """处理查看已有策略的逻辑"""
    db_manager = DBSessionManager()
    try:
        with db_manager as session: # 使用上下文管理器
            configs = session.query(GridConfig).order_by(GridConfig.id).all()
    except Exception as e:
        print(f"查询策略列表时出错: {e}")
        input("\n按任意键返回...")
        return

    def display_config(cfg: GridConfig):
        last_modified_str = cfg.last_modified.strftime("%Y-%m-%d %H:%M") if cfg.last_modified else "无"
        name_str = cfg.name if cfg.name else "无名称"
        return f"ID: {cfg.id:<4} | 名称: {name_str:<15} | a={cfg.a:<4.2f} | b={cfg.b:<4.2f} | 行数: {cfg.total_rows:<3} | 修改: {last_modified_str}"

    if not display_list_with_index(configs, "查看已有策略", display_config):
        input("\n按任意键返回...")
        return

    choice = get_index_input(len(configs))
    if choice == 'b' or choice is None: return

    selected_config = configs[choice - 1]
    choice_id = selected_config.id

    try:
        with db_manager as session:
            rows = session.query(GridRow).filter(GridRow.config_id == choice_id).order_by(GridRow.id).all()
    except Exception as e:
        print(f"查询策略详情时出错: {e}")
        input("\n按任意键返回...")
        return

    if not rows:
        print(f"\n❌ 未找到策略 ID {choice_id} 的详细行数据。")
    else:
        print(f"\n--- 策略 ID: {choice_id} ({selected_config.name or '无名称'}) 详情 ---")
        try:
            dict_rows = [row.to_dict() for row in rows]
            print_structured_grid_result(dict_rows) # 打印表格
        except Exception as e:
            print(f"格式化或打印策略详情时出错: {e}")

    input("\n按任意键返回...")


def handle_import_market_data():
    """处理导入行情数据的逻辑"""
    clear()
    print("=== 导入行情数据 (.xlsx) ===")
    print("\n请确保 Excel 文件第一行为表头，且包含以下列名:")
    print("- 日期Date (格式: YYYYMMDD 整数)")
    print("- 指数代码Index Code")
    print("- 指数中文全称Index Chinese Name(Full)")
    print("- 指数中文简称Index Chinese Name")
    # ... (可以省略一些不太重要的列名说明)
    print("- 开盘Open, 最高High, 最低Low, 收盘Close")
    print("- 涨跌幅(%)Change(%)")
    print("- ... (其他可选列)")
    print("-" * 30)

    print("将弹出文件选择框选择 Excel 文件...")
    # time.sleep(1.5) # 可以去掉，让用户直接操作

    # --- 使用 tkinter 选择文件 ---
    root = tk.Tk()
    root.withdraw()
    excel_file_path = filedialog.askopenfilename(
        title="选择 Excel 行情数据文件",
        filetypes=[("Excel files", "*.xlsx *.xls")]
    )
    root.destroy()
    # ---------------------------

    if not excel_file_path:
        print("\n❌ 未选择文件，操作取消。")
        time.sleep(1.5)
        return

    print(f"\n已选择文件: {excel_file_path}")
    original_filename = os.path.basename(excel_file_path)

    # --- 定义中间 JSON 路径 ---
    # 确保 data/database_folder 存在
    data_folder = os.path.join("data", "database_folder")
    os.makedirs(data_folder, exist_ok=True)
    json_file_path = os.path.join(data_folder, f"{os.path.splitext(original_filename)[0]}_temp_import.json")

    # --- 执行转换和导入 ---
    print("\n1. 正在将 Excel 转换为 JSON...")
    convert_success = False
    try:
        # 调用 util/init_to_json.py 中的函数
        convert_success = excel_to_json(excel_file_path, json_file_path)
        if convert_success: print(f"✅ JSON 文件已生成: {json_file_path}")
        else: print("❌ Excel 转 JSON 失败 (请检查文件格式和内容)。")
    except Exception as e:
        print(f"❌ Excel 转 JSON 时发生错误: {e}")
        # traceback.print_exc()

    if not convert_success:
        input("\n按任意键返回..."); return

    print("\n2. 正在将 JSON 数据导入数据库...")
    importer = None
    import_success = False
    try:
        importer = DataImporter(SQLALCHEMY_DATABASE_URI) # 使用导入的 URI
        import_success = importer.import_market_data_from_json(json_file_path, original_filename) # 传入文件名
        # 成功信息在 importer 内部打印
        if not import_success: print("❌ 数据导入数据库失败。")
    except Exception as e:
        print(f"❌ 数据导入时发生严重错误: {e}")
        # traceback.print_exc()
    finally:
        if importer: importer.close() # 确保关闭 session
        # 清理临时 JSON 文件
        if os.path.exists(json_file_path):
            try:
                os.remove(json_file_path)
                # 不再打印清理信息，保持界面简洁
                # if import_success: print(f"已清理临时 JSON 文件。")
            except Exception as e_clean:
                print(f"警告：清理临时 JSON 文件 '{json_file_path}' 失败: {e_clean}")

    input("\n按任意键返回...")


def handle_view_market_data():
    """查看现有数据 - 简化版，不分页，返回列表"""
    db_manager = DBSessionManager()
    while True: # 外层循环，用于查看详情后返回列表
        try:
            with db_manager as session:
                # 使用 db_function_library.py 中定义的 get_all_imported_files
                imported_files = db_manager.get_all_imported_files()
        except Exception as e:
            print(f"查询导入列表时出错: {e}"); input("\n按任意键返回..."); return

        def display_import_info(f: ImportedFiles):
             return f"ID: {f.id:<4} | 文件: {f.file_name or 'N/A':<25} | Code: {f.index_code:<8} | 记录: {f.record_count or 'N/A':<5} | 日期: {f.date_range or 'N/A'}"

        if not display_list_with_index(imported_files, "查看现有数据 (按导入批次)", display_import_info):
            input("\n按任意键返回..."); return # 直接返回上级菜单

        choice = get_index_input(len(imported_files))
        if choice == 'b' or choice is None: return # 返回上级菜单

        selected_import_record = imported_files[choice - 1]
        selected_import_id = selected_import_record.id

        # --- 获取选中 import_id 的 GridData 数据 ---
        try:
             with db_manager as session:
                 # 使用 get_record_by_any 获取列表
                 records = db_manager.get_record_by_any('GridData', import_id=selected_import_id)
                 # 手动按日期排序
                 records.sort(key=lambda x: x.date)
        except Exception as e:
             print(f"查询 Import ID {selected_import_id} 的数据时出错: {e}")
             input("\n按任意键返回列表..."); continue # 返回列表

        # --- 显示简化信息和预览 ---
        clear()
        print(f"--- 数据详情 (Import ID: {selected_import_id}, 文件: {selected_import_record.file_name or 'N/A'}) ---")
        if not records:
             print("未找到相关行情数据。")
        else:
             total_records = len(records)
             print(f"共 {total_records} 条记录。")
             # 假设同一批次 code 相同
             print(f"Index Code: {records[0].index_code}")
             # 使用 ImportedFiles 表中的日期范围，如果存在的话
             date_range_str = selected_import_record.date_range or f"{records[0].date.strftime('%Y-%m-%d')} ~ {records[-1].date.strftime('%Y-%m-%d')}"
             print(f"日期范围: {date_range_str}")

             # 只显示前 5 条和后 5 条作为预览
             preview_count = 5
             display_records = []
             if total_records <= 2 * preview_count:
                 display_records = records
             else:
                 display_records = records[:preview_count] + records[-preview_count:]

             headers = ["原始行号", "日期", "开盘", "最高", "最低", "收盘", "涨跌幅(%)"]
             display_data = []
             for i, r in enumerate(display_records):
                 # 查找记录在原始完整列表中的索引 (需要原始数据按日期排序)
                 original_index = records.index(r) + 1 # 找到对象在列表中的位置
                 display_data.append([
                     original_index, # 显示原始序号
                     r.date.strftime('%Y-%m-%d'), r.open_price, r.high_price,
                     r.low_price, r.close_price, r.change_percent
                 ])

             print("\n--- 数据预览 (部分数据) ---")
             print(tabulate(display_data, headers=headers, tablefmt="grid", floatfmt=".2f"))
             if total_records > 2 * preview_count:
                 print(f"... (共 {total_records} 条) ...")

        input("\n按任意键返回列表...") # 查看完详情后返回批次列表

def handle_delete_market_data():
    """处理删除行情数据（按导入批次）的逻辑"""
    db_manager = DBSessionManager() # 创建实例以便调用方法

    try:
        # 注意：get_all_imported_files 需要在 session 上下文之外或内部创建 session
        # 为简单起见，这里直接调用，依赖 DBSessionManager 内部的 session
        imported_files = db_manager.get_all_imported_files()
    except Exception as e:
        print(f"查询导入列表时出错: {e}"); input("\n按任意键返回..."); return
    finally:
        # 如果 get_all_imported_files 需要 session，确保关闭
        # db_manager.close() # 如果 DBSessionManager 有 close 方法
        pass # 假设 get_all_imported_files 内部管理 session 或 DBSessionManager 实例可重用

    def display_import_info_for_delete(f: ImportedFiles):
         return f"ID: {f.id:<4} | 文件: {f.file_name or 'N/A':<25} | Code: {f.index_code:<8} | 记录: {f.record_count or 'N/A':<5}"

    if not display_list_with_index(imported_files, "删除行情数据 (选择要删除的导入批次)", display_import_info_for_delete):
        input("\n按任意键返回..."); return

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
        # 需要一个新的 DBSessionManager 实例来执行删除操作并管理事务
        delete_manager = DBSessionManager()
        try:
             # 调用修正后的 delete_import_batch
             delete_success = delete_manager.delete_import_batch(selected_import_id)
             if not delete_success:
                 print("删除操作失败。") # delete_import_batch 内部会打印详细错误
        except Exception as e:
             print(f"执行删除时发生意外错误: {e}")
             # traceback.print_exc()
        finally:
             delete_manager.close() # 确保关闭 session
    else:
        print("操作已取消。")

    input("\n按任意键返回...")

def handle_backtest():
    """处理开始回测的逻辑"""
    clear()
    print("=== 开始回测 ===")
    db_manager = DBSessionManager() # 用于查询

    # --- 步骤 1: 选择策略 (按序号) ---
    try:
        with db_manager as session:
            configs = session.query(GridConfig).order_by(GridConfig.id).all()
    except Exception as e:
        print(f"查询策略列表时出错: {e}"); input("\n按任意键返回..."); return

    def display_config_for_backtest(cfg):
        name_str = cfg.name if cfg.name else "无名称"
        return f"ID: {cfg.id:<4} | 名称: {name_str:<15} | a={cfg.a:<4.2f} | b={cfg.b:<4.2f} | 行数: {cfg.total_rows:<3}"

    if not display_list_with_index(configs, "1. 请选择要回测的策略", display_config_for_backtest, show_empty_message=False):
        print("没有可用的策略。"); input("\n按任意键返回..."); return

    strategy_choice = get_index_input(len(configs))
    if strategy_choice == 'b' or strategy_choice is None: return
    selected_config = configs[strategy_choice - 1]
    strategy_id = selected_config.id

    try:
        with db_manager as session:
            grid_rows = session.query(GridRow).filter(GridRow.config_id == strategy_id).order_by(GridRow.id).all()
    except Exception as e:
        print(f"查询策略详情时出错: {e}"); input("\n按任意键返回..."); return
    if not grid_rows: print(f"❌ 策略 {strategy_id} 详情未找到。"); input("\n按任意键返回..."); return
    grid_strategy = [row.to_dict() for row in grid_rows]

    # --- 步骤 2: 选择数据 (按导入批次序号) ---
    try:
        with db_manager as session:
            imported_files = session.query(ImportedFiles).order_by(ImportedFiles.id).all()
    except Exception as e:
        print(f"查询数据批次列表时出错: {e}"); input("\n按任意键返回..."); return

    def display_import_info_for_backtest(f: ImportedFiles):
         return f"ID: {f.id:<4} | 文件: {f.file_name or 'N/A':<25} | Code: {f.index_code:<8} | 日期: {f.date_range or 'N/A'}"

    if not display_list_with_index(imported_files, "2. 请选择用于回测的数据批次", display_import_info_for_backtest, show_empty_message=False):
        print("没有可用的回测数据。"); input("\n按任意键返回..."); return

    data_choice = get_index_input(len(imported_files))
    if data_choice == 'b' or data_choice is None: return
    selected_import_record = imported_files[data_choice - 1]
    selected_import_id = selected_import_record.id

    # --- 加载选定 import_id 的 GridData ---
    try:
        with db_manager as session:
            grid_data_list = session.query(IndexData).filter(IndexData.import_id == selected_import_id).order_by(IndexData.date).all()
    except Exception as e:
        print(f"加载行情数据时出错: {e}"); input("\n按任意键返回..."); return
    if not grid_data_list: print(f"❌ 未找到 Import ID {selected_import_id} 的行情数据。"); input("\n按任意键返回..."); return
    grid_data = [row.to_dict() for row in grid_data_list] # 转换为字典

    # --- 执行回测 ---
    clear()
    print(f"--- 正在开始回测 ---")
    print(f"策略: {selected_config.name or strategy_id} (ID: {strategy_id})")
    print(f"数据: 文件 '{selected_import_record.file_name or 'N/A'}', Code '{selected_import_record.index_code}', Import ID {selected_import_id}")
    print("-" * 30 + "\n")
    try:
        # 假设 BackTest 初始化需要 initial_capital，如果不传会内部计算
        backtest = BackTest(grid_data, grid_strategy)
        result = backtest.run_backtest() # run_backtest 内部打印流水和快照

        print("\n" + "-" * 30)
        print("--- 回测指标总结 ---")
        metrics = result.get("metrics", {})
        print(f"初始资金 (推断): {metrics.get('initial_capital', 0):,.2f}")
        # 处理指标可能为 None 或非数值的情况
        def format_metric(value, format_str):
            if isinstance(value, (int, float)):
                try: return format(value, format_str)
                except (ValueError, TypeError): return str(value)
            return value or 'N/A'

        print(f"策略 XIRR: {format_metric(metrics.get('xirr'), '.2%')}")
        print(f"最大回撤: {format_metric(metrics.get('max_drawdown'), '.2%')}")
        print(f"年化夏普比: {format_metric(metrics.get('sharpe'), '.2f')}")
        print(f"年化波动率: {format_metric(metrics.get('volatility'), '.2%')}")
        print("-" * 30)

    except Exception as e:
        print(f"\n⚠️ 回测过程中发生错误: {e}")
        # traceback.print_exc() # 调试用

    input("\n按任意键返回主菜单...")


# --- 主程序入口 ---
# 注意：这部分应该放在 app.py 文件中
# if __name__ == "__main__":
#     # 可以在这里添加一些启动前的检查，比如数据库文件是否存在等
#     run_cli()