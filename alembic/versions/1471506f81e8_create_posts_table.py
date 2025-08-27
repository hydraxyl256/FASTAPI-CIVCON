"""create posts table

Revision ID: 1471506f81e8
Revises: 
Create Date: 2025-08-26 08:41:14.577576

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1471506f81e8'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('posts', sa.Column('id', sa.Integer(), nullable=False, primary_key=True), 
    sa.Column('title', sa.String(), nullable=False),  schema='public')
    pass


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('posts')
    pass
