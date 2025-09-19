import os
import time,sys
from dao.grid_data_structure import GridConfig
from util.build_grid_model import generate_grid_from_input,print_structured_grid_result,save_grid_to_db,print_grid_result_by_id
from dao.db_function_library import init_db
try:
    import msvcrt
    WINDOWS = True
except ImportError:
    import select
    WINDOWS = False

def run_cli():
    init_db()
    menu = {
        '1': ('生成模型策略', handle_generate),
        '2': ('查看历史策略', handle_view_history),
        '3': ('退出', None)
    }

    while True:
        clear()
        print("=== 网格交易神器 ===")
        for key, (label, _) in menu.items():
            print(f"{key}. {label}")

        choice = input("输入选项: ").strip()
        if choice not in menu:
            print("❌ 无效选项，请重新输入！")
            time.sleep(1.5)
            continue

        label, action = menu[choice]
        if choice == '3':  # 退出
            print("👋 再见")
            break

        # 执行对应功能
        try:
            action()
        except Exception as e:
            print(f"⚠️ 功能执行出错: {e}")
            input("按回车返回主菜单...")
            
def generate_grid_get_input():
    print("请输入网格参数：")
    
    name = input("请输入策略名称 (可选): ").strip() or None

    a = input_float("请输入波动捕捉大小参数 a (0.05~0.30): ", 0.05, 0.30)
    b = input_float("请输入每行收益率参数 b (0.05~0.30): ", 0.05, 0.30)
    first_trigger_price = input_float("请输入首个触发价 (例如 1.000): ", 0.0001)
    total_rows = input_int("请输入总行数 (例如 5): ", 1)
    buy_amount = input_float("请输入每次买入金额 (例如 10000.0): ", 0.01)

    params = {
        "name": name,
        "a": a,
        "b": b,
        "first_trigger_price": first_trigger_price,
        "total_rows": total_rows,
        "buy_amount": buy_amount
    }
    return generate_grid_from_input(params)
    

def handle_generate():
    clear()
    result = generate_grid_get_input()
    print("\n✅ 网格策略生成完成！")
    print("按回车键立即查看详情，或等待 5 秒后自动保存...")

    timeout = 5
    for remaining in range(timeout, 0, -1):
        print(f"保存倒计时：{remaining} 秒", end="\r", flush=True)

        if WINDOWS:
            # Windows: 用 msvcrt 检测是否按键
            if msvcrt.kbhit():
                key = msvcrt.getwch()
                if key == '\r':  # 回车键
                    print("\n--- 生成的策略数据 ---")
                    print_structured_grid_result(result)
                    print("是否保存该策略？ (y/n): ", end='', flush=True)
                    choice = input().strip().lower()
                    if choice == 'y':
                        save_grid_to_db(result)
                        print("✅ 策略已保存到数据库！")
                    else:
                        print("❌ 策略未保存。")
                    input("\n按回车返回主菜单...")
                    return
        else:
            # Linux/macOS: 用 select 检测是否有输入
            r, _, _ = select.select([sys.stdin], [], [], 1)
            if r:
                sys.stdin.readline()
                print("\n--- 生成的策略数据 ---")
                print_structured_grid_result(result)
                print("是否保存该策略？ (y/n): ", end='', flush=True)
                choice = input().strip().lower()
                if choice == 'y':
                    save_grid_to_db(result)
                    print("✅ 策略已保存到数据库！")
                else:
                    print("❌ 策略未保存。")
                input("\n按回车返回主菜单...")
                return

        time.sleep(1)

    print("\n⏪ 超时未操作，自动返回主菜单...")
    time.sleep(1)
def handle_view_history():
    clear()
    print("=== 历史策略列表 ===")
    configs = get_all_grid_configs()
    if not configs:
        print("📭 暂无策略记录")
        input("按回车返回主菜单...")
        return

    print("{:<4} {:<20} {:<20} {:<5} {:<5} {:<5}".format(
        "ID", "名称", "最后修改时间", "a", "b", "行数"
    ))
    for cfg in configs:
        print("{:<4} {:<20} {:<20} {:<5} {:<5} {:<5}".format(
            cfg.id, cfg.name, cfg.last_modified.strftime("%Y-%m-%d %H:%M"),
            cfg.a, cfg.b, cfg.total_rows
        ))

    choice = input("请输入要查看的策略 ID: ").strip()
    selected = get_grid_config_by_id(choice)
    if not selected:
        print("❌ 未找到该策略 ID")
        input("按回车返回主菜单...")
        return

    print_grid_result_by_id(selected.id)
    input("按回车返回主菜单...")
    
    
def input_float(prompt, min_value=None, max_value=None):
    while True:
        try:
            value = float(input(prompt))
            if min_value is not None and value < min_value:
                print(f"❌ 值必须 ≥ {min_value}")
                continue
            if max_value is not None and value > max_value:
                print(f"❌ 值必须 ≤ {max_value}")
                continue
            return value
        except ValueError:
            print("❌ 请输入一个数字")

def input_int(prompt, min_value=None, max_value=None):
    while True:
        try:
            value = int(input(prompt))
            if min_value is not None and value < min_value:
                print(f"❌ 值必须 ≥ {min_value}")
                continue
            if max_value is not None and value > max_value:
                print(f"❌ 值必须 ≤ {max_value}")
                continue
            return value
        except ValueError:
            print("❌ 请输入一个整数")


def clear():
    os.system('cls' if os.name == 'nt' else 'clear')