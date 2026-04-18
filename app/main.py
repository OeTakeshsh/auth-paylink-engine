import asyncio
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from contextlib import asynccontextmanager

from app.core.database import engine, Base
from app.core.config import settings
from app.core.logging import setup_logging
from app.middleware.correlation import CorrelationIdMiddleware

from app.routes import (
    user_router,
    health_router,
    payment_links_router,
    webhook_router
)

setup_logging(level="info")

@asynccontextmanager
async def lifespan(_: FastAPI):
    print("settings:", settings.model_dump())

    for attempt in range(5):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
                print("db connected")
                break
        except Exception as e:
            print(f"db not ready yet (attempt {attempt + 1}): {e}")
            await asyncio.sleep(2)
    else:
        print("could not connect to the database")

    yield

# Create the FastAPI app WITHOUT OAuth2 configuration
app = FastAPI(
    title="project management api",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    # Don't add security here - we'll do it in custom_openapi
)

# Custom OpenAPI configuration to add Bearer auth for Swagger
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="Project Management API",
        version="1.0.0",
        description="API for managing payment links and payments",
        routes=app.routes,
    )
    
    # Add security scheme for Bearer token (manual paste)
    openapi_schema["components"] = openapi_schema.get("components", {})
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": (
                "Paste your access token here.\n\n"
                "How to get your token:\n"
                "1. Use the POST /users/login endpoint with JSON body:\n"
                '   {"username": "your_email@example.com", "password": "your_password"}\n'
                "2. Copy the 'access_token' value from the response\n"
                "3. Paste it below and click Authorize"
            )
        }
    }
    
    # Apply security globally to all endpoints
    openapi_schema["security"] = [{"BearerAuth": []}]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

# Override the default openapi schema with our custom one
app.openapi = custom_openapi

app.add_middleware(CorrelationIdMiddleware)

app.include_router(health_router)
app.include_router(user_router)
app.include_router(payment_links_router)
app.include_router(webhook_router)

@app.get("/")
def root():
    return {"status": "ok"}
