from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import setup_logging
from app.graph.runtime import graph_runtime


@asynccontextmanager
async def lifespan(_: FastAPI):
    await graph_runtime.initialize()
    yield
    await graph_runtime.close()


def create_app() -> FastAPI:
    setup_logging()
    application = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description="AI-assisted shopping search API",
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "X-API-Key", "X-Conversation-Token"],
    )
    application.include_router(api_router, prefix="/api/v1")
    return application


app = create_app()
