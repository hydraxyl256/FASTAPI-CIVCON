"""update users table with new fields and role

Revision ID: 8ac28f88f20c
Revises: 0835781cc631
Create Date: 2025-08-30 10:35:52.258123

"""
from typing import Sequence, Union
from sqlalchemy.dialects.postgresql import ENUM
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text


# revision identifiers, used by Alembic.
revision: str = '8ac28f88f20c'
down_revision: Union[str, Sequence[str], None] = '0835781cc631'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""  


    # Create Role enum
    role_enum = ENUM('citizen', 'mp', 'admin', 'journalist', name='role', create_type=True)
    role_enum.create(op.get_bind(), checkfirst=True)

    # Drop existing search_vector column and trigger
    op.execute('DROP TRIGGER IF EXISTS tsvectorupdate ON users')
    op.drop_column('users', 'search_vector')

    # Recreate search_vector as a regular TSVECTOR column
    op.add_column('users', sa.Column('search_vector', sa.dialects.postgresql.TSVECTOR, nullable=True))

    # Add new columns with temporary nullable=True (skip email if it exists)
    op.add_column('users', sa.Column('full_name', sa.String(), nullable=True))
    op.add_column('users', sa.Column('nin', sa.String(), nullable=True, unique=True))
    op.add_column('users', sa.Column('constituency', sa.String(), nullable=True))
    op.add_column('users', sa.Column('district', sa.String(), nullable=True))
    op.add_column('users', sa.Column('sub_county', sa.String(), nullable=True))
    op.add_column('users', sa.Column('gender', sa.String(), nullable=True))
    op.add_column('users', sa.Column('date_of_birth', sa.Date(), nullable=True))
    op.add_column('users', sa.Column('phone_number', sa.String(), nullable=True))
    # Check if email column exists before adding
    conn = op.get_bind()
    email_exists = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='email'")).fetchone()
    if not email_exists:
        op.add_column('users', sa.Column('email', sa.String(), nullable=True, unique=True))
    op.add_column('users', sa.Column('role', role_enum, nullable=False, server_default='citizen'))
    op.add_column('users', sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'))

    # Populate existing rows
    op.execute("""
        UPDATE users
        SET
            full_name = COALESCE(username, email, 'Unknown User'),
            nin = 'NIN' || id || '-' || created_at::text,
            constituency = 'Unknown',
            district = 'Unknown',
            sub_county = 'Unknown',
            gender = 'Unknown',
            date_of_birth = '2000-01-01',
            phone_number = '0000000000',
            search_vector = to_tsvector('english', username)
        WHERE full_name IS NULL
    """)

    # Set NOT NULL constraints
    op.alter_column('users', 'full_name', nullable=False)
    op.alter_column('users', 'nin', nullable=False)
    op.alter_column('users', 'constituency', nullable=False)
    op.alter_column('users', 'district', nullable=False)
    op.alter_column('users', 'sub_county', nullable=False)
    op.alter_column('users', 'gender', nullable=False)
    op.alter_column('users', 'date_of_birth', nullable=False)
    op.alter_column('users', 'phone_number', nullable=False)

    # Create GIN index and trigger for search_vector
    op.create_index('users_search_vector_idx', 'users', ['search_vector'], postgresql_using='gin')
    op.execute("""
        CREATE TRIGGER tsvectorupdate BEFORE INSERT OR UPDATE
        ON users FOR EACH ROW EXECUTE FUNCTION
        tsvector_update_trigger(search_vector, 'pg_catalog.english', username, full_name);
    """)
    # Update search_vector for existing rows
    op.execute("UPDATE users SET search_vector = to_tsvector('english', username || ' ' || full_name)")
    



    pass


def downgrade() -> None:
    """Downgrade schema."""

    # Drop search_vector trigger and index
    op.execute('DROP TRIGGER IF EXISTS tsvectorupdate ON users')
    op.execute('DROP INDEX IF EXISTS users_search_vector_idx')
    op.drop_column('users', 'search_vector')

    # Drop new columns
    op.drop_column('users', 'full_name')
    op.drop_column('users', 'nin')
    op.drop_column('users', 'constituency')
    op.drop_column('users', 'district')
    op.drop_column('users', 'sub_county')
    op.drop_column('users', 'gender')
    op.drop_column('users', 'date_of_birth')
    op.drop_column('users', 'phone_number')
    op.drop_column('users', 'role')
    op.drop_column('users', 'is_active')

    # Recreate search_vector as a generated column (assuming original setup)
    op.add_column('users', sa.Column('search_vector', sa.dialects.postgresql.TSVECTOR, server_default=sa.text("to_tsvector('english', username)"), nullable=False))
    op.create_index('users_search_vector_idx', 'users', ['search_vector'], postgresql_using='gin')
    op.execute('DROP TYPE role')


    pass
