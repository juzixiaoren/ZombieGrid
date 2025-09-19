import os
import time,sys
from util.build_grid_model import generate_grid_from_input,print_structured_grid_result
try:
    import msvcrt
    WINDOWS = True
except ImportError:
    import select
    WINDOWS = False

def run_cli():
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
    a = input_float("请输入波动捕捉大小参数 a (0.05~0.30): ", 0.05, 0.30)
    b = input_float("请输入每行收益率参数 b (0.05~0.30): ", 0.05, 0.30)
    first_trigger_price = input_float("请输入首个触发价 (例如 1.000): ", 0.0001)
    total_rows = input_int("请输入总行数 (例如 5): ", 1)
    buy_amount = input_float("请输入每次买入金额 (例如 10000.0): ", 0.01)

    params = {
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
    print("按回车键立即查看详情，或等待 5 秒自动返回主菜单...")

    timeout = 5
    for remaining in range(timeout, 0, -1):
        print(f"返回主菜单倒计时：{remaining} 秒", end="\r", flush=True)

        if WINDOWS:
            # Windows: 用 msvcrt 检测是否按键
            if msvcrt.kbhit():
                key = msvcrt.getwch()
                if key == '\r':  # 回车键
                    print("\n--- 生成的策略数据 ---")
                    print_structured_grid_result(result)
                    input("\n按回车返回主菜单...")
                    return
        else:
            # Linux/macOS: 用 select 检测是否有输入
            r, _, _ = select.select([sys.stdin], [], [], 1)
            if r:
                sys.stdin.readline()
                print("\n--- 生成的策略数据 ---")
                print_structured_grid_result(result)
                input("\n按回车返回主菜单...")
                return

        time.sleep(1)

    print("\n⏪ 超时未操作，自动返回主菜单...")
    time.sleep(1)
def handle_view_history():
    clear()
    print("=== 历史策略列表 ===")
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