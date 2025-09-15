# ZombieGrid

网格交易神器

### 1. 文件结构？

```
ZombieGrid/
├── .gitignore
├── README.md
├── requirements.txt
├── main.py    # 主程序入口
│
├── venv/    # 整个项目的 python 虚拟环境
│
├── data/    # 存放历史数据csv
│   ├── .gitkeep
│   └── csi_399971_data.csv
│
└── src/    # 核心代码，需要import到main.py
    └── __init__.py    # 空文件，标记src目录作为包
    └── xxx.py
```

### 2. 部署和开发

- 配置虚拟环境（确保在根目录）
```Shell
python -m venv venv # 创建虚拟环境
source venv/bin/activate # 激活虚拟环境
```

- 安装 / 更新依赖

```Shell
pip install -r requirements.txt # 根据requirement.txt安装依赖
```

```Shell
pip freeze > requirements.txt # 更新现在用到的依赖到requirements.txt
```

- 运行程序

```Shell
python main.py
```

