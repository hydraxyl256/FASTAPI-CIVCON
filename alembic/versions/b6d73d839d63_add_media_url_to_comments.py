"""Add media_url to comments

Revision ID: b6d73d839d63
Revises: 98c3f4f3f512
Create Date: 2025-08-29 14:03:01.918437

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b6d73d839d63'
down_revision: Union[str, Sequence[str], None] = '98c3f4f3f512'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('comments', sa.Column('media_url', sa.String, nullable=True))
    pass


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('comments', 'media_url')
    pass
