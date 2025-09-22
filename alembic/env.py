import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context
from app.models import Base
from app.config import settings

config = context.config
connectable = create_async_engine(settings.database_url, echo=True)

async def run_migrations_online():
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=Base.metadata
    )
    with context.begin_transaction():
        context.run_migrations()

if context.is_offline_mode():
    raise NotImplementedError("Offline mode not supported with async engine")
else:
    asyncio.run(run_migrations_online())