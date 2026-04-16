from app.core.config import settings
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)
from sqlalchemy.orm import DeclarativeBase
from typing import AsyncGenerator

#Engine
engine = create_async_engine(
    settings.database_url,
    echo=True,
)

#Session Factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
    )

#SQLAlquemy se usa para definir modelos
class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependencia de FastAPI para obtener una sesión de base de datos.
    Se cierra automáticamente al finalizar la request.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
