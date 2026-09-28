from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.observability import configure_logging, request_context
from app.routers import health


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings)
    app = FastAPI(title="Monsieur Français API", version="0.1.0")
    app.middleware("http")(request_context)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    return app


app = create_app()
