# alembic/versions/1cded23f365d_add_importedfiles_table_and_import_id_.py
"""Add ImportedFiles table and import_id to GridData

Revision ID: 1cded23f365d
Revises: aaa00a9abfe5
Create Date: 2025-10-25 17:17:47.446467  # 这里的创建日期保持不变

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from datetime import datetime # 导入 datetime

# revision identifiers, used by Alembic.
revision: str = '1cded23f365d'
down_revision: Union[str, Sequence[str], None] = 'aaa00a9abfe5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. 创建 ImportedFiles 表 (使用你的命名)
    op.create_table('ImportedFiles',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False, comment='单次导入的股价数据xlsx的主键ID'),
        sa.Column('file_name', sa.String(length=255), nullable=True, comment='股价xlsx的文件名'), # 你的命名
        sa.Column('index_code', sa.String(length=50), nullable=False, comment='指数代码'),
        sa.Column('import_time', sa.DateTime(), nullable=True, comment='导入的时间'), # 你的命名
        sa.Column('record_count', sa.Integer(), nullable=True, comment='此次导入的记录数'),
        sa.Column('date_range', sa.String(length=50), nullable=True, comment='数据日期范围("YYYY-MM-DD ~ YYYY-MM-DD")'),
        sa.PrimaryKeyConstraint('id')
    )

    # 2. 向 ImportedFiles 插入代表现有数据的记录，文件名为 '399971perf.xlsx'
    #    index_code 根据你的 GridData 示例是 '399971'
    op.execute(
        f"INSERT INTO \"ImportedFiles\" (file_name, index_code, import_time) "
        f"VALUES ('399971perf.xlsx', '399971', '{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}');"
        # record_count 和 date_range 暂时留空 (NULL)
    )

    # 3. 添加 import_id 列到 GridData，先允许为空 (nullable=True)
    op.add_column('GridData', sa.Column('import_id', sa.Integer(), nullable=True, comment='从哪个ID的xlsx导入的')) # 注意这里 nullable=True

    # 4. 将现有 GridData 记录的 import_id 全部更新为 1
    op.execute('UPDATE "GridData" SET import_id = 1 WHERE import_id IS NULL')

    # 5. 使用 batch_alter_table 将 import_id 列修改为 NOT NULL
    #    这对于 SQLite 是必要的，因为它不支持直接 ALTER COLUMN SET NOT NULL
    with op.batch_alter_table('GridData', schema=None) as batch_op:
        batch_op.alter_column('import_id',
                              existing_type=sa.INTEGER(),
                              nullable=False) # 设置为 NOT NULL

    # 6. 使用 batch_alter_table 创建外键约束 (推荐在 NOT NULL 设置之后)
    with op.batch_alter_table('GridData', schema=None) as batch_op:
        batch_op.create_foreign_key(
            'fk_griddata_import_id',  # 指定约束名称
            'ImportedFiles',          # 参照表
            ['import_id'],            # 本地列
            ['id'],                   # 参照列
            ondelete='CASCADE'        # 当 ImportedFiles 记录删除时，关联的 GridData 也删除
        )


def downgrade() -> None:
    """Downgrade schema."""
    # 按相反的顺序撤销操作

    # 1. 使用 batch_alter_table 删除外键约束和列
    with op.batch_alter_table('GridData', schema=None) as batch_op:
        batch_op.drop_constraint('fk_griddata_import_id', type_='foreignkey') # 使用指定的名字删除约束
        batch_op.drop_column('import_id')

    # 2. 删除 ImportedFiles 表
    op.drop_table('ImportedFiles')