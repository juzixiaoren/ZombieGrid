# ZombieGrid (网格交易回测神器)
> 2025-9-22

本项目是一个基于命令行的量化交易回测工具，旨在实现并验证特定网格交易策略。

通过本工具，用户可以：
1.  根据5个核心参数动态生成网格交易策略。
2.  将生成的策略永久保存在本地SQLite数据库中。
3.  从数据库中读取并查看已保存的历史策略。
4.  使用指定的策略和历史行情数据，执行完整的回测并查看初步结果。

## 项目结构

```
ombieGrid/
├── 📄 alembic.ini             # Alembic的配置文件
├── 📄 app.py                  # ✅ 主程序入口
├── 📄 README.md               # 项目说明文档
│
├── 📂 alembic/                # 数据库版本管理、迁移工具
│
├── 📂 data/                   # 所有数据文件
│   ├── database_folder/      # 原始数据和中间文件
│   │   ├── 399971perf.xlsx   # 原始行情数据 (Excel版)
│   │   └── 399971perf.json   # 中间数据 (JSON版)
│   └── zombiegrid.db       # ✅ 核心：SQLite数据库文件
│
├── 📂 dao/                    # 数据库交互层 (Data Access Object)
│   ├── config.py             # 数据库连接配置
│   ├── grid_data_structure.py # ✅ 核心：定义了三张表的“长相”
│   ├── data_importer.py      # 将JSON数据导入数据库
│   └── db_function_library.py # 提供查询数据库的函数
│
├── 📂 service/                # 用户服务层
│   └── cli.py                # ✅ 前端命令行界面
│
└── 📂 util/                    # 核心算法与工具
    ├── build_grid_model.py   # ✅ 核心：生成网格策略的算法
    ├── backtest.py           # ✅ 核心：回测引擎的初步实现
    └── init_to_json.py       # 将Excel转换为JSON的工具脚本
```

## 环境搭建与运行指南

本项目使用 **Miniconda** 进行环境管理，使用 **pip** 进行依赖安装，以确保所有开发成员在不同操作系统（Windows, macOS, Linux）上都能拥有一致的开发环境。

---

### **第一步：安装 Miniconda**

如果你的电脑还没有安装，请根据你的操作系统，前往官网下载并安装。

* **官网地址**: [https://www.anaconda.com/download/success](https://www.anaconda.com/download/success)

**Windows 用户**: 建议选择 `.exe` 安装包，并在安装过程中勾选“Add Miniconda to my PATH environment variable”（将Miniconda添加到系统路径）选项。

---

### **第二步：创建并激活项目环境**

以下所有命令均在**项目根目录**（即 `ZombieGrid/` 目录）下通过命令行工具执行。

1.  **克隆代码库** (如果还没有):
    ```shell
    git clone [你的项目Git地址]
    cd ZombieGrid
    ```

2.  **创建Conda环境**:
    Conda会读取 `environment.yml` 文件，自动创建一个包含所有依赖的隔离环境。
    ```shell
    conda create -n ZombieGrid_venv python=3.9
    ```

3.  **激活环境**:
    ```shell
    conda activate ZombieGrid # 激活成功后，终端前应该会出现(ZombieGrid)标识。
    # 退出环境：conda deactivate
    ```

4.  **安装依赖**:
    ```shell
    pip install -r requirements.txt
    ```
4.  **更新依赖**:
    ```shell
    # 确保(ZombieGrid)环境激活
    pip freeze > requirements.txt
    ```

---

### **第三步：初始化数据库、导入历史行情数据**

数据库`zombiegrid.db`在开发阶段会上传到git，同步给所有成员。
因此本部分命令理论上不需要执行。

可以安装VScode的SQLite插件，直观查看.db的内容。

若未创建数据库，你需要使用Alembic工具根据代码模型，在 `data/` 目录下创建并初始化 `zombiegrid.db` 数据库文件。

* **确保你的Conda环境已激活 (`(ZombieGrid)`)**
* 运行以下命令：
    ```bash
    alembic upgrade head
    ```
    *执行成功后，你会在 `data/` 目录下看到 `zombiegrid.db` 文件。*


数据库已经建好，现在需要将用于回测的行情数据导入。

* **确保你的Conda环境已激活 (`(ZombieGrid)`)**
* **注意**: 导入过程分两步，请依次执行以下命令：

    1.  **将原始数据转换为JSON格式**:
        ```bash
        python -m util.init_to_json
        ```
    2.  **将JSON数据导入数据库**:
        ```bash
        python -m dao.data_importer
        ```
    *看到成功导入的提示后，你的数据库就已经准备就绪了。*

---

### **第四步：运行主程序**

完成以上所有步骤后，你就可以启动这个“网格交易神器”了！

* **确保你的Conda环境已激活 (`(ZombieGrid)`)
* 运行主程序 `app.py`:
    ```bash
    python app.py # macOS 可能需要使用 python3 命令
    ```
    *运行后，你将看到一个交互式的菜单，可以开始生成和回测你的交易策略。*

---

### 日常开发流程

* 每次开始开发前，请务-务必先用 `conda activate ZombieGrid` 激活环境。随后进行依赖同步、更新。开发结束后，可以使用 `conda deactivate` 退出环境。