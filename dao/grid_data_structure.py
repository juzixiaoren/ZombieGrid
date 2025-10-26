from sqlalchemy import Column, Integer, String, Float, Date,ForeignKey,DateTime
from sqlalchemy.orm import relationship,declarative_base
from datetime import datetime

Base = declarative_base()

class BaseModel:
    """基础模型类，提供通用方法"""
    def to_dict(self):
        data = {}
        for c in self.__table__.columns:
            val = getattr(self, c.name)
            if isinstance(val, datetime):
                val = val.strftime("%Y-%m-%d %H:%M:%S")  # 格式化为字符串
            data[c.name] = val
        return data
    

class ImportedFiles(Base, BaseModel):
    """ 导入的原始xlsx的信息，每一次导入都有一个主键id """
    __tablename__ = 'ImportedFiles'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='单次导入的股价数据xlsx的主键ID')
    file_name = Column(String(255), nullable=True, comment='股价xlsx的文件名')
    index_code = Column(String(50), nullable=False, comment='指数代码')
    import_time = Column(DateTime, default=datetime.utcnow, comment='导入的时间')
    record_count = Column(Integer, nullable=True, comment='此次导入的记录数')
    date_range = Column(String(50), nullable=True, comment='数据日期范围("YYYY-MM-DD ~ YYYY-MM-DD")')

    def __repr__(self):
        return f"<ImportedFiles(id={self.id}, file_name='{self.file_name}',index_code='{self.index_code}')>"

    
class IndexData(Base,BaseModel):
    """
    存储导入的指数回测数据，每条有一个import_id属性记录来源于哪一次导入，属性有日期、指数代码等
    """
    __tablename__ = 'GridData'
    
    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 字段定义
    import_id = Column(Integer, ForeignKey('ImportedFiles.id', ondelete="CASCADE"), nullable=False, comment='从哪个ID的xlsx导入的')
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
        return f"<IndexData(date='{self.date}', index_code='{self.index_code}',import_id='{self.import_id}')>"
    


class GridConfig(Base, BaseModel):
    """ 存储每个策略的配置参数，一个策略一行 """
    __tablename__ = 'GridConfig'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=True, comment="策略名称")
    last_modified = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="最后修改时间")
    a = Column(Float, nullable=False, comment="波动大小参数 a")
    b = Column(Float, nullable=False, comment="单行收益率参数 b")
    first_trigger_price = Column(Float, nullable=False, comment="首行买入触发价")
    total_rows = Column(Integer, nullable=False, comment="网格总行数")
    buy_amount = Column(Float, nullable=False, comment="买入金额")

    #created_at = Column(DateTime, default=datetime.utcnow)  # 添加时间戳
    
    # 关联关系：一个配置对应多个网格行
    rows = relationship("GridRow", back_populates="config", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<GridConfig(id={self.id})>"
    


class GridRow(Base, BaseModel):
    """ 存储每个策略，一个策略total_rows行 """
    __tablename__ = 'GridRow'

    id = Column(Integer, primary_key=True, autoincrement=True)
    config_id = Column(Integer, ForeignKey('GridConfig.id', ondelete="CASCADE"), nullable=False, comment="所属配置ID")
    fall_percent = Column(Float, nullable=False, comment="跌幅比例")
    level_ratio = Column(Float, nullable=False, comment="档位值")
    buy_trigger_price = Column(Float, nullable=False, comment="买入触发价")
    buy_price = Column(Float, nullable=False, comment="买入交易价")
    buy_amount = Column(Float, nullable=False, comment="买入金额")
    shares = Column(Float, nullable=False, comment="买入股数")

    sell_trigger_price = Column(Float, nullable=False, comment="卖出触发价")
    sell_price = Column(Float, nullable=False, comment="卖出交易价")
    yield_rate = Column(Float, nullable=False, comment="收益率")
    profit_amount = Column(Float, nullable=False, comment="盈利金额")
    # 关联回配置
    config = relationship("GridConfig", back_populates="rows")

    def __repr__(self):
        return f"<GridRow(config_id={self.config_id})>"