"""add user profile fields for signup

Revision ID: 967f1719e303
Revises: 0b647ed4d51b
Create Date: 2025-08-31 08:34:38.034714

"""
from typing import Sequence, Union
from sqlalchemy.dialects.postgresql import JSONB
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '967f1719e303'
down_revision: Union[str, Sequence[str], None] = '0b647ed4d51b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.add_column('users', sa.Column('region', sa.String(), nullable=True))
    op.add_column('users', sa.Column('parish', sa.String(), nullable=True))
    op.add_column('users', sa.Column('village', sa.String(), nullable=True))
    op.add_column('users', sa.Column('bio', sa.String(), nullable=True))
    op.add_column('users', sa.Column('political_interest', sa.String(), nullable=True))
    op.add_column('users', sa.Column('community_role', sa.String(), nullable=True))
    op.add_column('users', sa.Column('occupation', sa.String(), nullable=True))
    op.add_column('users', sa.Column('interests', JSONB(), nullable=True))
    op.add_column('users', sa.Column('notification_email', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('users', sa.Column('notification_sms', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('notification_push', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('users', sa.Column('profile_image', sa.String(), nullable=True))

    # Populate existing rows
    op.execute("""
        UPDATE users
        SET
            region = 'Unknown',
            parish = 'Unknown',
            village = 'Unknown',
            bio = '',
            political_interest = '',
            community_role = '',
            occupation = '',
            interests = '[]'::jsonb,
            notification_email = true,
            notification_sms = false,
            notification_push = true,
            profile_image = NULL
    """)

    # Set NOT NULL constraints where needed
    op.alter_column('users', 'region', nullable=False)
    op.alter_column('users', 'parish', nullable=False)
    op.alter_column('users', 'village', nullable=False)





    pass


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_column('users', 'profile_image')
    op.drop_column('users', 'notification_push')
    op.drop_column('users', 'notification_sms')
    op.drop_column('users', 'notification_email')
    op.drop_column('users', 'interests')
    op.drop_column('users', 'occupation')
    op.drop_column('users', 'community_role')
    op.drop_column('users', 'political_interest')
    op.drop_column('users', 'bio')
    op.drop_column('users', 'village')
    op.drop_column('users', 'parish')
    op.drop_column('users', 'region')



    pass
