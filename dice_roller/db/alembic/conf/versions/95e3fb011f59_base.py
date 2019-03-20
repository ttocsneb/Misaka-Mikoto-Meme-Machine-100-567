"""base

Revision ID: 95e3fb011f59
Revises: 
Create Date: 2019-03-06 14:11:14.630589

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '95e3fb011f59'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():

    op.create_table(
        'servers',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('prefix', sa.String(1))
    )
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True)
    )
    op.create_table(
        'association',
        sa.Column('server_id', sa.Integer(), sa.ForeignKey('servers.id')),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'))
    )


def downgrade():
    op.drop_table('servers')
    op.drop_table('users')
    op.drop_table('association')
