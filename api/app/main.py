from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.errors import ForbiddenError, NotFoundError, TooManyRequestsError, UnauthorizedError
from app.jobs.scheduler import lifespan
from app.observability import configure_logging, configure_tracing, request_context
from app.routers import (
    auth,
    budget,
    glossary,
    health,
    lessons,
    library,
    notes,
    path,
    search,
    settings,
    skills,
    speaking,
    writing,
)
from app.services.budget import BudgetExceededError


async def _budget_exceeded(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, BudgetExceededError)
    return JSONResponse(
        status_code=402,
        content={"detail": str(exc), "cap": exc.cap_name, "cap_usd": str(exc.cap)},
    )


def _status(code: int) -> Callable[[Request, Exception], Awaitable[JSONResponse]]:
    async def handler(_: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=code, content={"detail": str(exc)})

    return handler


def create_app() -> FastAPI:
    config = get_settings()
    configure_logging(config)
    app = FastAPI(title="Monsieur Français API", version="0.1.0", lifespan=lifespan)
    app.middleware("http")(request_context)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.exception_handler(BudgetExceededError)(_budget_exceeded)
    app.exception_handler(NotFoundError)(_status(404))
    app.exception_handler(ForbiddenError)(_status(403))
    app.exception_handler(UnauthorizedError)(_status(401))
    app.exception_handler(TooManyRequestsError)(_status(429))
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(budget.router)
    app.include_router(path.router)
    app.include_router(lessons.router)
    app.include_router(library.router)
    app.include_router(glossary.router)
    app.include_router(notes.router)
    app.include_router(skills.router)
    app.include_router(settings.router)
    app.include_router(writing.router)
    app.include_router(search.router)
    app.include_router(speaking.router)
    # Only shared catalogue audio is public; learners' own recordings are never mounted.
    catalog = config.media_dir / "catalog"
    catalog.mkdir(parents=True, exist_ok=True)
    app.mount("/media/catalog", StaticFiles(directory=catalog), name="catalog-media")
    configure_tracing(app, config)
    return app


app = create_app()
