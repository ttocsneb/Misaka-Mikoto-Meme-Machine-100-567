"""add RollStats

Revision ID: 9d6b3231a6fe
Revises: 46e3b7f2961b
Create Date: 2019-03-08 23:40:48.381086

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9d6b3231a6fe'
down_revision = '46e3b7f2961b'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'rollstats',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String()),
        sa.Column('value', sa.String())
    )

    with op.batch_alter_table('stats') as batch_op:
        batch_op.add_column(sa.Column('calc', sa.Float()))


def downgrade():
    op.drop_table('rollstats')

    with op.batch_alter_table('stats') as batch_op:
        batch_op.drop_column('calc')
