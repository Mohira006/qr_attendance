import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.database import SessionLocal, engine
from app.core.exceptions import register_exception_handlers
from app.services import photo_storage, scheduler, settings_service
from app.websocket.routes import router as websocket_router

logging.basicConfig(
    level=logging.DEBUG if get_settings().DEBUG else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    config = get_settings()
    photo_storage.ensure_directories()
    # Make sure the single settings row exists so every request can rely on it.
    async with SessionLocal() as db:
        await settings_service.get_or_create(db)
    scheduler.start()
    logger.info("%s started (environment=%s, timezone=%s)", config.APP_NAME, config.ENVIRONMENT, config.COMPANY_TIMEZONE)
    yield
    scheduler.shutdown()
    await engine.dispose()


def create_app() -> FastAPI:
    config = get_settings()
    app = FastAPI(
        title=config.APP_NAME,
        version="0.1.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[config.FRONTEND_URL],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_exception_handlers(app)
    app.include_router(api_router)
    app.include_router(websocket_router)

    @app.get("/api/health", tags=["system"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "environment": config.ENVIRONMENT}

    return app


app = create_app()
