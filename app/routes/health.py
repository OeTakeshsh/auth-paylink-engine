from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.logging import app_logger

router = APIRouter(prefix="/health", tags=["health"])

@router.get("/")
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    verifica el estado de la api y la base de datos.
    retorna 200 si todo esta bien, 503 si hay problemas.
    """
    try:
        # prueba simple de base de datos
        await db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as e:
        app_logger.error(f"health check failed: db error - {str(e)}")
        db_status = "error"

    if db_status == "ok":
        return {"status": "ok", "database": "connected"}
    else:
        # fast-api no tiene 503 por defecto, usamos 503 service unavailable
        from fastapi import Response
        return Response(
            status_code=503,
            content='{"status": "degraded", "database": "disconnected"}',
            media_type="application/json"
        )
