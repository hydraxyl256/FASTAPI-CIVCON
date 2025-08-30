"""add notifications table

Revision ID: 0835781cc631
Revises: 5028158213d1
Create Date: 2025-08-29 17:02:30.822185

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0835781cc631'
down_revision: Union[str, Sequence[str], None] = '5028158213d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'notifications',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('message', sa.String, nullable=False),
        sa.Column('is_read', sa.Boolean, default=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('post_id', sa.Integer, sa.ForeignKey('posts.id', ondelete='CASCADE'), nullable=True),
        sa.Column('group_id', sa.Integer, sa.ForeignKey('groups.id', ondelete='CASCADE'), nullable=True)
    )



    pass


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_table('notifications')

    pass
