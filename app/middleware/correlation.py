from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from uuid import uuid4
from app.core.context import correlation_id_ctx
from app.core.logging import app_logger

class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Extraer correlation ID del header o generar uno nuevo
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid4()))
        correlation_id_ctx.set(correlation_id)

        # Log de entrada
        app_logger.info(f"→ {request.method} {request.url.path}")

        try:
            response = await call_next(request)
            # Log de salida con status code
            app_logger.info(f"← {request.method} {request.url.path} - {response.status_code}")
        except Exception as e:
            app_logger.exception(f"✗ {request.method} {request.url.path} - Error: {str(e)}")
            raise

        response.headers["X-Correlation-ID"] = correlation_id
        return response
