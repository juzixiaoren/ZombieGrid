from .bayesian_opt import BayesianOptimizer
# from .genetic_opt import GeneticOptimizer (未来)

def get_optimizer(algo_type: str, market_data: list, initial_capital: float):
    """
    优化器工厂函数
    """
    if algo_type == 'bayes':
        return BayesianOptimizer(market_data, initial_capital)
    elif algo_type == 'genetic':
        raise NotImplementedError("遗传算法开发中...")
    else:
        raise ValueError(f"未知算法: {algo_type}")