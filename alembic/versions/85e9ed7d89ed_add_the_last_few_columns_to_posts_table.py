"""add the last few columns to posts table

Revision ID: 85e9ed7d89ed
Revises: 307c10f8805a
Create Date: 2025-08-26 12:32:59.100798
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '85e9ed7d89ed'
down_revision: Union[str, Sequence[str], None] = '307c10f8805a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('posts', sa.Column('content', sa.Text(), nullable=True))
    op.add_column('posts', sa.Column('published', sa.Boolean(), server_default='TRUE', index=True))
    op.add_column('posts', sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')))

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('posts', 'created_at')
    op.drop_column('posts', 'published')
    op.drop_column('posts', 'content')