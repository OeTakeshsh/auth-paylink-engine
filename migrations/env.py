import os   # <-- asegúrate de importar os
import sys
from pathlib import Path
from alembic import context
from sqlalchemy import create_engine
from app.core.database import Base
from app.core.config import settings
from app.models.user import User, UserToken   # <-- importa tus modelos

target_metadata = Base.metadata

def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    # Usar DATABASE_URL de entorno o el de settings
    url = os.getenv("DATABASE_URL", settings.database_url)
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    """Run migrations in 'online' mode (synchronous)."""
    # Usar DATABASE_URL de entorno o el de settings
    url = os.getenv("DATABASE_URL", settings.database_url)
    sync_url = url.replace("+asyncpg", "+psycopg2")
    connectable = create_engine(sync_url)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()
