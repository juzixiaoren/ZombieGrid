from sqlalchemy import Column, Integer, String, Float, Date, create_engine
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class IndexData(Base):
    """
    指数数据表结构 - 用于数据库存储
    """
    __tablename__ = 'GridData'
    
    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 字段定义
    date = Column(Date, nullable=False, comment='日期')
    index_code = Column(String(50), nullable=False, comment='指数代码')
    index_chinese_full_name = Column(String(100), nullable=False, comment='指数中文全称')
    index_chinese_short_name = Column(String(50), nullable=False, comment='指数中文简称')
    index_english_full_name = Column(String(100), nullable=False, comment='指数英文全称')
    index_english_short_name = Column(String(50), nullable=False, comment='指数英文简称')
    open_price = Column(Float, nullable=False, comment='开盘价')
    high_price = Column(Float, nullable=False, comment='最高价')
    low_price = Column(Float, nullable=False, comment='最低价')
    close_price = Column(Float, nullable=False, comment='收盘价')
    change = Column(Float, nullable=False, comment='涨跌')
    change_percent = Column(Float, nullable=False, comment='涨跌幅(%)')
    volume_m_shares = Column(Float, nullable=False, comment='成交量(万手)')
    turnover = Column(Float, nullable=False, comment='成交金额(亿元)')
    cons_number = Column(Integer, nullable=False, comment='样本数量')
    
    def __repr__(self):
        return f"<IndexData(date='{self.date}', index_code='{self.index_code}')>"