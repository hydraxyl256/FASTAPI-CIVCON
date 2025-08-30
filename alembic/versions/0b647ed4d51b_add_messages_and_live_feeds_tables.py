"""add messages and live_feeds tables

Revision ID: 0b647ed4d51b
Revises: 8ac28f88f20c
Create Date: 2025-08-30 11:26:46.430888

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0b647ed4d51b'
down_revision: Union[str, Sequence[str], None] = '8ac28f88f20c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.create_table(
        'messages',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('sender_id', sa.Integer, sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('recipient_id', sa.Integer, sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('content', sa.String, nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False)
    )
    op.create_table(
        'live_feeds',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('title', sa.String, nullable=False),
        sa.Column('stream_url', sa.String, nullable=False),
        sa.Column('description', sa.String, nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('journalist_id', sa.Integer, sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    )

    pass


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_table('live_feeds')
    op.drop_table('messages')

    pass
