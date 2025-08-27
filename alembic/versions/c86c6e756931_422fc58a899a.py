"""422fc58a899a

Revision ID: c86c6e756931
Revises: 422fc58a899a
Create Date: 2025-08-26 12:00:01.898372

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c86c6e756931'
down_revision: Union[str, Sequence[str], None] = '422fc58a899a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
