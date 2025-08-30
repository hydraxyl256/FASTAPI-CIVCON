"""Add view_count, categories, groups

Revision ID: 5028158213d1
Revises: b6d73d839d63
Create Date: 2025-08-29 15:24:12.820067

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5028158213d1'
down_revision: Union[str, Sequence[str], None] = 'b6d73d839d63'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

# Create groups table first
    op.create_table(
        'groups',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('name', sa.String, unique=True, nullable=False, index=True),
        sa.Column('description', sa.String, nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('owner_id', sa.Integer, sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    )
    
    # Create group_members table
    op.create_table(
        'group_members',
        sa.Column('group_id', sa.Integer, sa.ForeignKey('groups.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    )
    
    # Add view_count to posts
    op.add_column('posts', sa.Column('view_count', sa.Integer, nullable=False, server_default='0'))
    
    # Add group_id to posts
    op.add_column('posts', sa.Column('group_id', sa.Integer, sa.ForeignKey('groups.id', ondelete='SET NULL'), nullable=True))
    
    # Create categories table
    op.create_table(
        'categories',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('name', sa.String, unique=True, nullable=False, index=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()'))
    )
    
    # Create post_categories table
    op.create_table(
        'post_categories',
        sa.Column('post_id', sa.Integer, sa.ForeignKey('posts.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('category_id', sa.Integer, sa.ForeignKey('categories.id', ondelete='CASCADE'), primary_key=True))

    pass


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_table('post_categories')
    op.drop_table('categories')
    op.drop_column('posts', 'group_id')
    op.drop_column('posts', 'view_count')
    op.drop_table('group_members')
    op.drop_table('groups')

    pass
