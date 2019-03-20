"""base

Revision ID: 46e3b7f2961b
Revises: 
Create Date: 2019-03-06 14:03:51.855996

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '46e3b7f2961b'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():

    op.create_table(
        'stats',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column('name', sa.String()),
        sa.Column('value', sa.String())
    )

    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True)
    )

    op.create_table(
        'equations',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String()),
        sa.Column('equation', sa.String()),
        sa.Column('creator_id', sa.Integer(), sa.ForeignKey('users.id')),
        sa.Column('params', sa.Integer()),
        sa.Column('desc', sa.Integer())
    )

    op.create_table(
        'percs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('table_id', sa.Integer(), sa.ForeignKey('tables.id')),
        sa.Column('index', sa.Integer()),
        sa.Column('weight', sa.Integer()),
        sa.Column('value', sa.String())
    )

    op.create_table(
        'tables',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('creator_id', sa.Integer(), sa.ForeignKey('users.id')),
        sa.Column('name', sa.String()),
        sa.Column('desc', sa.String()),
        sa.Column('hidden', sa.Boolean())
    )

    op.create_table(
        'data',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('prefix', sa.String(1)),
        sa.Column('current_id', sa.Integer())
    )


def downgrade():
    op.drop_table('stats')
    op.drop_table('users')
    op.drop_table('equations')
    op.drop_table('percs')
    op.drop_table('tables')
    op.drop_table('data')
