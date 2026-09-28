from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.observability import configure_logging, request_context
from app.routers import budget, health
from app.services.budget import BudgetExceededError


async def _budget_exceeded(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, BudgetExceededError)
    return JSONResponse(
        status_code=402,
        content={"detail": str(exc), "cap": exc.cap_name, "cap_usd": str(exc.cap)},
    )


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
    app.exception_handler(BudgetExceededError)(_budget_exceeded)
    app.include_router(health.router)
    app.include_router(budget.router)
    return app


app = create_app()
