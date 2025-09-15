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
├── venv/    # 整个项目的 python 虚拟环境。使用 miniconda 管理
│
├── data/    # 存放历史数据csv
│   ├── .gitkeep
│   └── csi_399971_data.csv
│
└── src/    # 核心代码，需要import到main.py
    └── __init__.py    # 空文件，标记src目录作为包
    └── xxx.py
```

*temp：InitToJson.py作用是将excel文件转为json文件，并验证json文件格式是否正确；Import.py作用是将json文件导入到数据库中；DB_FunctionLibrary.py作用是提供一些数据库操作函数。*

### 2. 部署和开发

- 配置虚拟环境（确保在根目录）

先去官网下载Miniconda，如果有的选记得添加到PATH
1. 图形界面安装：https://www.anaconda.com/download/success
2. 命令行安装：https://www.anaconda.com/docs/getting-started/miniconda/install#windows-command-prompt
安装过Anaconda也可以直接用Anaconda。conda生态命令是几乎一样的。

- conda新建、激活、退出虚拟环境：
```Shell
conda create -n ZombieGrid_venv python=3.13 
# 只需要执行一次。这一步之后，会在conda目录/envs下创建一个ZombieGrid_venv/文件夹作为虚拟环境

conda activate ZombieGrid_venv
# 激活虚拟环境，一定要在激活时装依赖。激活成功后应出现 (ZombieGrid) 。

conda deactivate # 退出虚拟环境
```

- 安装 / 更新依赖（激活虚拟环境后）

```Shell
conda env update -f environment.yml 
# 根据 environment.yml 安装所有依赖（不会删除环境中已存在但yml中没有的包）

conda env update -f environment.yml --prune 
# 根据 environment.yml 安装/同步所有依赖（会确保环境与yml文件完全一致，删除多装的包）

conda install package_name # 安装某个特定的包

conda env export > environment.yml # 更新现在用到的依赖到requirements.txt
```

- 运行程序

```Shell
python main.py
```

