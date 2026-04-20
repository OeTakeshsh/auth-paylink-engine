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
    public_router,
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

    # Use the exact name that FastAPI expects: "HTTPBearer"
    openapi_schema["components"]["securitySchemes"] = {
        "HTTPBearer": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": (
                "⚠️ **IMPORTANT**: Swagger does NOT validate the token.\n\n"
                "1. Call `POST /users/login` with JSON:\n"
                '   `{"username": "email@example.com", "password": "your_password"}`\n'
                "2. Copy the `access_token` from the response.\n"
                "3. Paste it here and click Authorize.\n\n"
                "If the token is invalid or expired, endpoints will return 401."
            )
        }
    }

    # Mark the public endpoint as having no security
    public_path = "/payment-links/pay/"
    for path, path_item in openapi_schema["paths"].items():
        if path.startswith(public_path):
            for method, operation in path_item.items():
                operation["security"] = []   # remove security requirement

    app.openapi_schema = openapi_schema
    return app.openapi_schema

# Override the default openapi schema with our custom one
app.openapi = custom_openapi

app.add_middleware(CorrelationIdMiddleware)

app.include_router(health_router)
app.include_router(user_router)
app.include_router(payment_links_router)
app.include_router(webhook_router)
app.include_router(public_router)

@app.get("/")
def root():
    return {"status": "ok"}
