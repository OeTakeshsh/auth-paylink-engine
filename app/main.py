import asyncio
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.core.database import engine, Base
from app.routes import router,health       # router principal (users)
from app.routes.payment_links import router as payment_links_router # se cambio importacion con alias porque no cargaba directamente como router
from app.core.config import settings
from app.core.logging import setup_logging, app_logger
from app.middleware.correlation import CorrelationIdMiddleware

# configurar logging primero
setup_logging(level="INFO")

@asynccontextmanager
async def lifespan(_: FastAPI):
    # startup
    print("SETTINGS:", settings.model_dump())
    for attempt in range(5):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
                print('db connected')
                break
        except Exception as e:
            print(f"db not ready yet (attempt {attempt + 1}): {e}")
            await asyncio.sleep(2)
    else:
        print("could not connect to the database")
    yield

# crear app una sola vez
app = FastAPI(
    title="Project Management API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# agregar middlewares
app.add_middleware(CorrelationIdMiddleware)

# incluir routers
app.include_router(health.router)
app.include_router(router)
app.include_router(payment_links_router)

@app.get("/")
def root():
    return {"status": "ok"}
