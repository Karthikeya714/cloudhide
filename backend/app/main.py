"""CloudHide FastAPI application entrypoint."""
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import health
from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import init_db

configure_logging()
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    for directory in (
        "uploads",
        "encrypted",
        "fragments",
        "carriers",
        "stego",
        "recovered",
    ):
        (settings.storage_root_path / directory).mkdir(parents=True, exist_ok=True)

    init_db()
    logger.info("%s started in %s mode", settings.app_name, settings.environment)
    yield


app = FastAPI(
    title=settings.app_name,
    description="Secure encrypted file storage using adaptive image steganography.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error while processing %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


app.include_router(health.router)
app.include_router(api_router, prefix=settings.api_prefix)
