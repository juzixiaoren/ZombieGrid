import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from skopt import gp_minimize
from skopt.space import Real, Integer
from generate_data import load_market_from_db
import warnings
warnings.filterwarnings('ignore')

# -----------------------------
# 1. 配置：只需修改这一行
# -----------------------------
TARGET_COLUMN = '策略 XIRR'  # ←←← 在这里指定你的目标输出列（必须是下面5个之一）

# -----------------------------
# 2. 根据你的表格列名精确判断优化方向
# -----------------------------
if TARGET_COLUMN in ['策略 XIRR', '年化夏普比']:
    OPTIMIZE_MODE = 'maximize'
elif TARGET_COLUMN in ['最大回撤 (相对峰值)', '最大回撤 (相对初始)', '年化波动率']:
    OPTIMIZE_MODE = 'minimize'
else:
    raise ValueError(
        f"❌ 不支持的目标列: '{TARGET_COLUMN}'\n"
        "✅ 请使用以下列名之一:\n"
        "   - 最大化: '策略 XIRR', '年化夏普比'\n"
        "   - 最小化: '最大回撤 (相对峰值)', '最大回撤 (相对初始)', '年化波动率'"
    )

# -----------------------------
# 3. 加载你的 Excel 数据（文件名必须为 OutPut.xlsx）
# -----------------------------
try:
    df = pd.read_excel('OutPut.xlsx', engine='openpyxl')
    print(f"✅ 成功加载 'OutPut.xlsx'，共 {len(df)} 行数据")
except FileNotFoundError:
    raise FileNotFoundError("❌ 找不到 'OutPut.xlsx'，请确保该文件在当前目录")
except Exception as e:
    raise RuntimeError(f"❌ 读取 Excel 文件失败: {e}")

# 检查必要列是否存在
required_inputs = ['a', 'b', '首行买入触发价', '模型行数', '买入金额']
required_outputs = ['策略 XIRR', '最大回撤 (相对峰值)', '最大回撤 (相对初始)', '年化夏普比', '年化波动率']

missing_inputs = [col for col in required_inputs if col not in df.columns]
missing_outputs = [col for col in required_outputs if col not in df.columns]

if missing_inputs:
    raise ValueError(f"❌ 输入列缺失: {missing_inputs}")
if TARGET_COLUMN not in df.columns:
    raise ValueError(f"❌ 目标列 '{TARGET_COLUMN}' 不在数据中。可用列: {required_outputs}")

# 准备特征和目标
X = df[required_inputs]
y = df[TARGET_COLUMN]

# 删除目标列中的 NaN 行
initial_count = len(y)
valid_mask = y.notna()
X = X[valid_mask]
y = y[valid_mask]
final_count = len(y)

print(f"📊 数据过滤: {initial_count} → {final_count} 行 (移除 {initial_count - final_count} 行 NaN)")

# -----------------------------
# 4. 训练回归模型
# -----------------------------
print(f"🎯 目标: '{TARGET_COLUMN}' → 优化方向: {OPTIMIZE_MODE}")
print("⏳ 正在训练回归模型...")
model = RandomForestRegressor(n_estimators=200, random_state=42, n_jobs=-1)
model.fit(X, y)
print("✅ 回归模型训练完成")

# -----------------------------
# 5. 定义搜索空间（基于数据的实际范围）
# -----------------------------
def get_search_space(X):
    space = []
    for col in X.columns:
        if col == 'a':
            # 根据你的业务逻辑设置 a 的范围
            space.append(Real(0.05, 0.30, name=col))  # 示例：a ∈ [5%, 30%]
        elif col == 'b':
            # 根据你的业务逻辑设置 b 的范围
            space.append(Real(0.05, 0.3, name=col))  # 示例：b ∈ [5%, 30%]
        elif col == '首行买入触发价':
            market_data = load_market_from_db()
            first_low =  market_data [0]['low_price']
            space.append(Real(first_low, first_low * 1.5, name=col))
        elif col == '模型行数':
            space.append(Integer(5, 30, name=col))    # 整数范围
        elif col == '买入金额':
            space.append(Real(1000, 50000, name=col))
        else:
            # 兜底：动态边界（不应该触发）
            low = max(0, X[col].min() * 0.9)
            high = X[col].max() * 1.1
            if col == '模型行数':
                space.append(Integer(int(low), int(high), name=col))
            else:
                space.append(Real(low, high, name=col))
    return space

search_space = get_search_space(X)

# -----------------------------
# 6. 优化目标函数
# -----------------------------
def objective(input_values):
    x_input = np.array(input_values).reshape(1, -1)
    pred = model.predict(x_input)[0]
    # skopt 最小化，所以最大化目标需取负
    return -pred if OPTIMIZE_MODE == 'maximize' else pred

# -----------------------------
# 7. 执行贝叶斯优化
# -----------------------------
print("🔍 正在搜索局部最优输入组合（约需 30-60 秒）...")
result = gp_minimize(
    func=objective,
    dimensions=search_space,
    n_calls=100,
    n_initial_points=20,
    random_state=42,
    verbose=False
)

# -----------------------------
# 8. 输出结果
# -----------------------------
optimal_inputs = result.x
optimal_value = -result.fun if OPTIMIZE_MODE == 'maximize' else result.fun

print("\n" + "="*70)
print(f"🏆 最优策略参数 (目标: {TARGET_COLUMN})")
print("="*70)
print("【最优输入组合】")
for col, val in zip(required_inputs, optimal_inputs):
    if col == '模型行数':
        print(f"  {col:<12}: {int(round(val))}")
    else:
        print(f"  {col:<12}: {val:>10.4f}")

print(f"\n【预测的局部最优输出值】: {optimal_value:.6f}")
print("="*70)


# # -----------------------------
# # 9. 保存训练好的模型和结果
# # -----------------------------
# import joblib
# import json
# import os

# # 创建保存目录
# os.makedirs("saved_models", exist_ok=True)

# # 保存随机森林模型
# model_path = "saved_models/rf_model.pkl"
# joblib.dump(model, model_path)
# print(f"✅ 模型已保存至: {model_path}")

# # 保存最优参数
# required_inputs = ['a', 'b', '首行买入触发价', '模型行数', '买入金额']
# best_params = {}
# for col, val in zip(required_inputs, optimal_inputs):
#     if col == '模型行数':
#         best_params[col] = int(round(val))
#     else:
#         best_params[col] = float(val)
# best_params['最优目标值'] = float(optimal_value)
# best_params['目标列'] = TARGET_COLUMN
# best_params['优化方向'] = OPTIMIZE_MODE

# params_path = "saved_models/best_params.json"
# with open(params_path, 'w', encoding='utf-8') as f:
#     json.dump(best_params, f, ensure_ascii=False, indent=2)
# print(f"✅ 最优参数已保存至: {params_path}")

# # 保存搜索空间
# space_path = "saved_models/search_space.pkl"
# joblib.dump(search_space, space_path)
# print(f"✅ 搜索空间已保存至: {space_path}")