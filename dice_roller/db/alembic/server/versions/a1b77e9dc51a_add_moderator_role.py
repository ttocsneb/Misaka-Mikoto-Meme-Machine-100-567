"""Add Moderator Role

Revision ID: a1b77e9dc51a
Revises: 9d6b3231a6fe
Create Date: 2019-03-11 12:19:05.441077

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b77e9dc51a'
down_revision = '9d6b3231a6fe'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('data') as batch_op:
        batch_op.add_column(sa.Column('mod', sa.String()))


def downgrade():
    with op.batch_alter_table('data') as batch_op:
        batch_op.drop_column('mod')
