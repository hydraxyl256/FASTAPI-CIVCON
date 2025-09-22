"""Update to SQLAlchemy 2.0

Revision ID: 2a7a1599e6c3
Revises: 967f1719e303
Create Date: 2025-09-08 11:51:48.331523

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column

# revision identifiers, used by Alembic.
revision: str = '2a7a1599e6c3'
down_revision: Union[str, Sequence[str], None] = '967f1719e303'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Check if columns exist before adding (idempotent)
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {col['name'] for col in inspector.get_columns('users')}

    # Add new columns to users table only if they don't exist
    if 'region' not in existing_columns:
        op.add_column('users', sa.Column('region', sa.String(), nullable=True))
    if 'parish' not in existing_columns:
        op.add_column('users', sa.Column('parish', sa.String(), nullable=True))
    if 'village' not in existing_columns:
        op.add_column('users', sa.Column('village', sa.String(), nullable=True))
    if 'bio' not in existing_columns:
        op.add_column('users', sa.Column('bio', sa.String(), nullable=True))
    if 'political_interest' not in existing_columns:
        op.add_column('users', sa.Column('political_interest', sa.String(), nullable=True))
    if 'community_role' not in existing_columns:
        op.add_column('users', sa.Column('community_role', sa.String(), nullable=True))
    if 'occupation' not in existing_columns:
        op.add_column('users', sa.Column('occupation', sa.String(), nullable=True))
    if 'interests' not in existing_columns:
        op.add_column('users', sa.Column('interests', postgresql.JSONB(), nullable=True))
    if 'notification_email' not in existing_columns:
        op.add_column('users', sa.Column('notification_email', sa.Boolean(), server_default='true', nullable=False))
    if 'notification_sms' not in existing_columns:
        op.add_column('users', sa.Column('notification_sms', sa.Boolean(), server_default='false', nullable=False))
    if 'notification_push' not in existing_columns:
        op.add_column('users', sa.Column('notification_push', sa.Boolean(), server_default='true', nullable=False))
    if 'profile_image' not in existing_columns:
        op.add_column('users', sa.Column('profile_image', sa.String(), nullable=True))

    # Update users table with default values (safe to rerun)
    op.execute("""
        UPDATE users
        SET
            region = COALESCE(region, 'Unknown'),
            parish = COALESCE(parish, 'Unknown'),
            village = COALESCE(village, 'Unknown'),
            bio = COALESCE(bio, ''),
            political_interest = COALESCE(political_interest, ''),
            community_role = COALESCE(community_role, ''),
            occupation = COALESCE(occupation, ''),
            interests = COALESCE(interests, '[]'::jsonb),
            notification_email = COALESCE(notification_email, true),
            notification_sms = COALESCE(notification_sms, false),
            notification_push = COALESCE(notification_push, true),
            profile_image = COALESCE(profile_image, NULL)
    """)

    # Set NOT NULL constraints on users columns (safe to rerun)
    op.alter_column('users', 'region', existing_type=sa.String(), nullable=False)
    op.alter_column('users', 'parish', existing_type=sa.String(), nullable=False)
    op.alter_column('users', 'village', existing_type=sa.String(), nullable=False)

    # Other table migrations
    op.add_column('categories', sa.Column('description', sa.String(), nullable=True))
    op.drop_index(op.f('ix_categories_name'), table_name='categories')
    op.create_unique_constraint(None, 'categories', ['name'])
    op.drop_column('categories', 'created_at')
    op.add_column('comments', sa.Column('parent_comment_id', sa.Integer(), nullable=True))
    op.add_column('comments', sa.Column('is_active', sa.Boolean(), nullable=True))
    op.drop_constraint(op.f('comments_post_id_fkey'), 'comments', type_='foreignkey')
    op.drop_constraint(op.f('comments_user_id_fkey'), 'comments', type_='foreignkey')
    op.create_foreign_key(None, 'comments', 'posts', ['post_id'], ['id'])
    op.create_foreign_key(None, 'comments', 'users', ['user_id'], ['id'])
    op.create_foreign_key(None, 'comments', 'comments', ['parent_comment_id'], ['id'])
    op.drop_column('comments', 'media_url')
    op.drop_column('comments', 'search_vector')

    # Commented out to prevent error: user_id is part of primary key and must remain NOT NULL
    # op.alter_column('group_members', 'user_id', existing_type=sa.INTEGER(), nullable=True)

    # Commented out to prevent error: group_id is part of primary key and must remain NOT NULL
    # op.alter_column('group_members', 'group_id', existing_type=sa.INTEGER(), nullable=True)

    op.drop_constraint(op.f('group_members_group_id_fkey'), 'group_members', type_='foreignkey')
    op.drop_constraint(op.f('group_members_user_id_fkey'), 'group_members', type_='foreignkey')
    op.create_foreign_key(None, 'group_members', 'groups', ['group_id'], ['id'])
    op.create_foreign_key(None, 'group_members', 'users', ['user_id'], ['id'])
    op.add_column('groups', sa.Column('is_active', sa.Boolean(), nullable=True))
    op.drop_index(op.f('ix_groups_name'), table_name='groups')
    op.create_unique_constraint(None, 'groups', ['name'])
    op.drop_constraint(op.f('groups_owner_id_fkey'), 'groups', type_='foreignkey')
    op.drop_column('groups', 'owner_id')
    op.add_column('live_feeds', sa.Column('content', sa.String(), nullable=False))
    op.add_column('live_feeds', sa.Column('is_active', sa.Boolean(), nullable=True))
    op.drop_constraint(op.f('live_feeds_journalist_id_fkey'), 'live_feeds', type_='foreignkey')
    op.create_foreign_key(None, 'live_feeds', 'users', ['journalist_id'], ['id'])
    op.drop_column('live_feeds', 'description')
    op.drop_column('live_feeds', 'stream_url')
    op.add_column('messages', sa.Column('is_read', sa.Boolean(), nullable=True))
    op.drop_constraint(op.f('messages_sender_id_fkey'), 'messages', type_='foreignkey')
    op.drop_constraint(op.f('messages_recipient_id_fkey'), 'messages', type_='foreignkey')
    op.create_foreign_key(None, 'messages', 'users', ['recipient_id'], ['id'])
    op.create_foreign_key(None, 'messages', 'users', ['sender_id'], ['id'])
    op.add_column('notifications', sa.Column('content', sa.String(), nullable=False))
    op.drop_index(op.f('ix_notifications_user_id'), table_name='notifications')
    op.drop_constraint(op.f('notifications_user_id_fkey'), 'notifications', type_='foreignkey')
    op.drop_constraint(op.f('notifications_group_id_fkey'), 'notifications', type_='foreignkey')
    op.drop_constraint(op.f('notifications_post_id_fkey'), 'notifications', type_='foreignkey')
    op.create_foreign_key(None, 'notifications', 'users', ['user_id'], ['id'])
    op.drop_column('notifications', 'message')
    op.drop_column('notifications', 'post_id')
    op.drop_column('notifications', 'group_id')

    # Commented out to prevent error: post_id is part of primary key and must remain NOT NULL
    # op.alter_column('post_categories', 'post_id', existing_type=sa.INTEGER(), nullable=True)

    # Commented out to prevent error: category_id is part of primary key and must remain NOT NULL
    # op.alter_column('post_categories', 'category_id', existing_type=sa.INTEGER(), nullable=True)

    op.drop_constraint(op.f('post_categories_category_id_fkey'), 'post_categories', type_='foreignkey')
    op.drop_constraint(op.f('post_categories_post_id_fkey'), 'post_categories', type_='foreignkey')
    op.create_foreign_key(None, 'post_categories', 'categories', ['category_id'], ['id'])
    op.create_foreign_key(None, 'post_categories', 'posts', ['post_id'], ['id'])

    # Posts table updates - handle search_vector dependency first
    posts_columns = {col['name'] for col in inspector.get_columns('posts')}

    # Add title column as nullable first (idempotent)
    if 'title' not in posts_columns:
        op.add_column('posts', sa.Column('title', sa.String(), nullable=True))
    # Populate title column with title_of_the_post or a default value
    op.execute("UPDATE posts SET title = COALESCE(title, title_of_the_post, 'Untitled')")
    # Set title column to NOT NULL
    op.alter_column('posts', 'title', existing_type=sa.String(), nullable=False)

    op.add_column('posts', sa.Column('is_active', sa.Boolean(), nullable=True))
    op.drop_index(op.f('ix_posts_content'), table_name='posts')
    op.drop_index(op.f('ix_posts_published'), table_name='posts')
    op.drop_index(op.f('ix_posts_title_of_the_post'), table_name='posts')
    op.drop_constraint(op.f('posts_users_fkey'), 'posts', type_='foreignkey')
    op.drop_constraint(op.f('posts_group_id_fkey'), 'posts', type_='foreignkey')
    op.create_foreign_key(None, 'posts', 'groups', ['group_id'], ['id'])
    op.create_foreign_key(None, 'posts', 'users', ['owner_id'], ['id'])

    # Drop search_vector index if it exists (idempotent)
    op.execute("DROP INDEX IF EXISTS ix_posts_search_vector")

    # Drop search_vector column (it exists)
    op.drop_column('posts', 'search_vector')

    # Now safe to drop title_of_the_post
    op.drop_column('posts', 'title_of_the_post')

    # Recreate search_vector using new 'title' column (adjust expression if needed based on your original model)
    op.add_column('posts', sa.Column(
        'search_vector',
        postgresql.TSVECTOR(),
        sa.Computed("to_tsvector('english', coalesce(title, '') || ' ' || coalesce(content, ''))", persisted=True),
        nullable=True
    ))
    # Create GIN index on search_vector (standard for TSVECTOR; idempotent if already exists, but since we dropped it, it's fine)
    op.create_index('ix_posts_search_vector', 'posts', ['search_vector'], postgresql_using='gin')

    op.drop_column('posts', 'view_count')
    op.drop_column('posts', 'published')
    op.alter_column('users', 'email',
               existing_type=sa.VARCHAR(),
               nullable=True)
    op.alter_column('users', 'is_active',
               existing_type=sa.BOOLEAN(),
               nullable=True,
               existing_server_default=sa.text('true'))
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_index(op.f('users_search_vector_idx'), table_name='users', postgresql_using='gin')
    op.create_unique_constraint(None, 'users', ['username'])

    # Votes table updates - handle NOT NULL for existing data
    votes_columns = {col['name'] for col in inspector.get_columns('votes')}
    if 'vote_type' not in votes_columns:
        # Add column as nullable first
        op.add_column('votes', sa.Column('vote_type', sa.String(), nullable=True))
        # Backfill existing rows with a default value (adjust 'up' if needed, e.g., based on a 'value' column)
        votes_table = table('votes', column('vote_type'))
        op.execute(votes_table.update().values(vote_type='up'))
        # Now set to NOT NULL
        op.alter_column('votes', 'vote_type', existing_type=sa.String(), nullable=False)

    op.drop_constraint(op.f('votes_post_id_fkey'), 'votes', type_='foreignkey')
    op.drop_constraint(op.f('votes_user_id_fkey'), 'votes', type_='foreignkey')
    op.create_foreign_key(None, 'votes', 'posts', ['post_id'], ['id'])
    op.create_foreign_key(None, 'votes', 'users', ['user_id'], ['id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(None, 'votes', type_='foreignkey')
    op.drop_constraint(None, 'votes', type_='foreignkey')
    op.create_foreign_key(op.f('votes_user_id_fkey'), 'votes', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key(op.f('votes_post_id_fkey'), 'votes', 'posts', ['post_id'], ['id'], ondelete='CASCADE')
    # Drop vote_type (no backfill needed for downgrade)
    op.drop_column('votes', 'vote_type')
    op.drop_constraint(None, 'users', type_='unique')
    op.create_index(op.f('users_search_vector_idx'), 'users', ['search_vector'], unique=False, postgresql_using='gin')
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    op.alter_column('users', 'is_active',
               existing_type=sa.BOOLEAN(),
               nullable=False,
               existing_server_default=sa.text('true'))
    op.alter_column('users', 'email',
               existing_type=sa.VARCHAR(),
               nullable=False)

    # Posts downgrade - reverse search_vector handling
    # Drop new search_vector index if exists (idempotent)
    op.execute("DROP INDEX IF EXISTS ix_posts_search_vector")

    # Drop new search_vector
    op.drop_column('posts', 'search_vector')

    # Add back title_of_the_post and populate from title
    op.add_column('posts', sa.Column('title_of_the_post', sa.String(), nullable=True))
    op.execute("UPDATE posts SET title_of_the_post = COALESCE(title_of_the_post, title)")
    op.alter_column('posts', 'title_of_the_post', existing_type=sa.String(), nullable=False)
    op.drop_column('posts', 'title')

    # Recreate old search_vector using title_of_the_post (adjust expression if needed)
    op.add_column('posts', sa.Column(
        'search_vector',
        postgresql.TSVECTOR(),
        sa.Computed("to_tsvector('english', coalesce(title_of_the_post, '') || ' ' || coalesce(content, ''))", persisted=True),
        nullable=True
    ))
    # Recreate GIN index
    op.create_index('ix_posts_search_vector', 'posts', ['search_vector'], postgresql_using='gin')

    op.add_column('posts', sa.Column('published', sa.BOOLEAN(), server_default=sa.text('true'), autoincrement=False, nullable=True))
    op.add_column('posts', sa.Column('view_count', sa.INTEGER(), server_default=sa.text('0'), autoincrement=False, nullable=False))
    op.drop_constraint(None, 'posts', type_='foreignkey')
    op.drop_constraint(None, 'posts', type_='foreignkey')
    op.create_foreign_key(op.f('posts_group_id_fkey'), 'posts', 'groups', ['group_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key(op.f('posts_users_fkey'), 'posts', 'users', ['owner_id'], ['id'], ondelete='CASCADE')
    op.create_index(op.f('ix_posts_title_of_the_post'), 'posts', ['title_of_the_post'], unique=False)
    op.create_index(op.f('ix_posts_published'), 'posts', ['published'], unique=False)
    op.create_index(op.f('ix_posts_content'), 'posts', ['content'], unique=False)
    op.drop_column('posts', 'is_active')
    op.drop_constraint(None, 'post_categories', type_='foreignkey')
    op.drop_constraint(None, 'post_categories', type_='foreignkey')
    op.create_foreign_key(op.f('post_categories_post_id_fkey'), 'post_categories', 'posts', ['post_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key(op.f('post_categories_category_id_fkey'), 'post_categories', 'categories', ['category_id'], ['id'], ondelete='CASCADE')
    # Ensure post_id and category_id remain NOT NULL to maintain primary key integrity
    op.alter_column('post_categories', 'category_id',
               existing_type=sa.INTEGER(),
               nullable=False)
    op.alter_column('post_categories', 'post_id',
               existing_type=sa.INTEGER(),
               nullable=False)
    op.add_column('notifications', sa.Column('group_id', sa.INTEGER(), autoincrement=False, nullable=True))
    op.add_column('notifications', sa.Column('post_id', sa.INTEGER(), autoincrement=False, nullable=True))
    op.add_column('notifications', sa.Column('message', sa.VARCHAR(), autoincrement=False, nullable=False))
    op.drop_constraint(None, 'notifications', type_='foreignkey')
    op.create_foreign_key(op.f('notifications_post_id_fkey'), 'notifications', 'posts', ['post_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key(op.f('notifications_group_id_fkey'), 'notifications', 'groups', ['group_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key(op.f('notifications_user_id_fkey'), 'notifications', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    op.create_index(op.f('ix_notifications_user_id'), 'notifications', ['user_id'], unique=False)
    op.drop_column('notifications', 'content')
    op.drop_constraint(None, 'messages', type_='foreignkey')
    op.drop_constraint(None, 'messages', type_='foreignkey')
    op.create_foreign_key(op.f('messages_recipient_id_fkey'), 'messages', 'users', ['recipient_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key(op.f('messages_sender_id_fkey'), 'messages', 'users', ['sender_id'], ['id'], ondelete='CASCADE')
    op.drop_column('messages', 'is_read')
    op.add_column('live_feeds', sa.Column('stream_url', sa.VARCHAR(), autoincrement=False, nullable=False))
    op.add_column('live_feeds', sa.Column('description', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.drop_constraint(None, 'live_feeds', type_='foreignkey')
    op.create_foreign_key(op.f('live_feeds_journalist_id_fkey'), 'live_feeds', 'users', ['journalist_id'], ['id'], ondelete='CASCADE')
    op.drop_column('live_feeds', 'is_active')
    op.drop_column('live_feeds', 'content')
    op.add_column('groups', sa.Column('owner_id', sa.INTEGER(), autoincrement=False, nullable=False))
    op.create_foreign_key(op.f('groups_owner_id_fkey'), 'groups', 'users', ['owner_id'], ['id'], ondelete='CASCADE')
    op.drop_constraint(None, 'groups', type_='unique')
    op.create_index(op.f('ix_groups_name'), 'groups', ['name'], unique=True)
    op.drop_column('groups', 'is_active')
    op.drop_constraint(None, 'group_members', type_='foreignkey')
    op.drop_constraint(None, 'group_members', type_='foreignkey')
    op.create_foreign_key(op.f('group_members_user_id_fkey'), 'group_members', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key(op.f('group_members_group_id_fkey'), 'group_members', 'groups', ['group_id'], ['id'], ondelete='CASCADE')
    # Ensure group_id and user_id remain NOT NULL to maintain primary key integrity
    op.alter_column('group_members', 'group_id',
               existing_type=sa.INTEGER(),
               nullable=False)
    op.alter_column('group_members', 'user_id',
               existing_type=sa.INTEGER(),
               nullable=False)
    op.add_column('comments', sa.Column('search_vector', postgresql.TSVECTOR(), sa.Computed("to_tsvector('english'::regconfig, (content)::text)", persisted=True), autoincrement=False, nullable=True))
    op.add_column('comments', sa.Column('media_url', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.drop_constraint(None, 'comments', type_='foreignkey')
    op.drop_constraint(None, 'comments', type_='foreignkey')
    op.drop_constraint(None, 'comments', type_='foreignkey')
    op.create_foreign_key(op.f('comments_user_id_fkey'), 'comments', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key(op.f('comments_post_id_fkey'), 'comments', 'posts', ['post_id'], ['id'], ondelete='CASCADE')
    op.drop_column('comments', 'is_active')
    op.drop_column('comments', 'parent_comment_id')
    op.add_column('categories', sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False))
    op.drop_constraint(None, 'categories', type_='unique')
    op.create_index(op.f('ix_categories_name'), 'categories', ['name'], unique=True)
    op.drop_column('categories', 'description')