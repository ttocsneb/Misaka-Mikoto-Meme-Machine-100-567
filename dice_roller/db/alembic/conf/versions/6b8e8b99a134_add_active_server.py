"""Add active server

Revision ID: 6b8e8b99a134
Revises: 95e3fb011f59
Create Date: 2019-03-06 14:27:50.394424

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6b8e8b99a134'
down_revision = '95e3fb011f59'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(sa.Column('active_server_id', sa.Integer()))
        batch_op.create_foreign_key("fk_active_server", 'servers', 
                                    ['active_server_id'], ['id'])


def downgrade():
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('active_server_id')
