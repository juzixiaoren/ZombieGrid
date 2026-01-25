from abc import ABC, abstractmethod

class BaseOptimizer(ABC):
    """优选算法基类"""
    
    def __init__(self, market_data: list, initial_capital: float):
        """
        :param market_data: IndexData 对象转字典后的列表
        :param initial_capital: 初始资金
        """
        self.market_data = market_data
        self.initial_capital = initial_capital
        
    @abstractmethod
    def run(self, **kwargs) -> dict:
        """
        执行优化
        :return: 包含最佳参数的字典 {'a':..., 'b':..., 'first_trigger_price':..., ...}
        """
        pass