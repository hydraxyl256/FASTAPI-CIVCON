"""add foriegn-keys to posts table

Revision ID: 307c10f8805a
Revises: c86c6e756931
Create Date: 2025-08-26 12:08:08.671875

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '307c10f8805a'
down_revision: Union[str, Sequence[str], None] = 'c86c6e756931'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('posts', sa.Column('owner_id', sa.Integer(), nullable=False))
    op.create_foreign_key('posts_users_fkey', source_table="posts", referent_table="users",
    local_cols=["owner_id"], remote_cols=["id"], ondelete='CASCADE')
    pass


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('owner_id', table_name='posts')
    op.drop_column('posts', 'owner_id')
    pass
