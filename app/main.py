import asyncio
from fastapi import FastAPI
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
        except exception as e:
            print(f"db not ready yet (attempt {attempt + 1}): {e}")
            await asyncio.sleep(2)
    else:
        print("could not connect to the database")

    yield

app = FastAPI(
    title="project management api",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

app.add_middleware(CorrelationIdMiddleware)

app.include_router(health_router)
app.include_router(user_router)
app.include_router(payment_links_router)
app.include_router(webhook_router)

@app.get("/")
def root():
    return {"status": "ok"}
