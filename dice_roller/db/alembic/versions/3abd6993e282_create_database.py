"""Create Database

Revision ID: 3abd6993e282
Revises: 
Create Date: 2019-05-16 18:24:04.020190

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3abd6993e282'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():

    op.create_table(
        'user',
        sa.Column('id', sa.BigInteger, primary_key=True),
        sa.Column('active_server_id', sa.BigInteger, sa.ForeignKey('server.id'))
    )

    op.create_table(
        'server',
        sa.Column('id', sa.BigInteger, primary_key=True),
        sa.Column('prefix', sa.String(1), default='?'),
        sa.Column('auto_add_stats', sa.Boolean, default=True),
        sa.Column('mod_id', sa.BigInteger, nullable=True)
    )

    op.create_table(
        'stat',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.BigInteger, sa.ForeignKey('user.id')),
        sa.Column('server_id', sa.BigInteger, sa.ForeignKey('server.id')),
        sa.Column('name', sa.String(16)),
        sa.Column('value', sa.String(45)),
        sa.Column('calc', sa.Float, nullable=True),
        sa.Column('group', sa.String(16), nullable=True)
    )

    op.create_table(
        'rollstat',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('server_id', sa.BigInteger, sa.ForeignKey('server.id')),
        sa.Column('name', sa.String(16)),
        sa.Column('value', sa.String(45)),
        sa.Column('group', sa.String(16), nullable=True)
    )

    op.create_table(
        'table',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('creator_id', sa.BigInteger, sa.ForeignKey('user.id')),
        sa.Column('server_id', sa.BigInteger, sa.ForeignKey('server.id')),
        sa.Column('name', sa.String(16)),
        sa.Column('desc', sa.String(32), nullable=True),
        sa.Column('hidden', sa.Boolean, default=False)
    )

    op.create_table(
        'tableitem',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('table_id', sa.Integer, sa.ForeignKey('table.id')),
        sa.Column('index', sa.Integer),
        sa.Column('weight', sa.Integer, default=1),
        sa.Column('value', sa.String(64))
    )

    op.create_table(
        'equation',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('creator_id', sa.BigInteger, sa.ForeignKey('user.id')),
        sa.Column('server_id', sa.BigInteger, sa.ForeignKey('server.id')),
        sa.Column('name', sa.String(16)),
        sa.Column('desc', sa.String(32), nullable=True),
        sa.Column('value', sa.String(45)),
        sa.Column('params', sa.Integer, default=0)
    )

    op.create_table(
        'server_user',
        sa.Column('server_id', sa.BigInteger, sa.ForeignKey('server.id')),
        sa.Column('user_id', sa.BigInteger, sa.ForeignKey('user.id'))
    )


def downgrade():
    op.drop_table('user')
    op.drop_table('server')
    op.drop_table('stat')
    op.drop_table('rollstat')
    op.drop_table('table')
    op.drop_table('tableitem')
    op.drop_table('equation')
    op.drop_table('server_user')
