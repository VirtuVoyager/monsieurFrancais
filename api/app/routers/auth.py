from typing import Annotated

from fastapi import APIRouter, Cookie, Request, Response

from app.config import get_settings
from app.db import SessionDep
from app.errors import UnauthorizedError
from app.models import User
from app.schemas.auth import AuthStatus, Passphrase
from app.services import auth
from app.services.users import get_or_create_learner

router = APIRouter(prefix="/auth", tags=["auth"])
SessionCookie = Annotated[str | None, Cookie(alias=auth.COOKIE_NAME)]


@router.get("/status")
def status(session: SessionDep, token: SessionCookie = None) -> AuthStatus:
    user = get_or_create_learner(session)
    return AuthStatus(
        configured=user.passphrase_hash is not None,
        authenticated=auth.user_id_from(token) == user.id,
    )


@router.post("/setup", status_code=204)
def setup(body: Passphrase, session: SessionDep, response: Response) -> None:
    user = get_or_create_learner(session)
    auth.set_passphrase(session, user, body.passphrase)
    _start_session(response, user)


@router.post("/login", status_code=204)
def login(body: Passphrase, session: SessionDep, request: Request, response: Response) -> None:
    user = get_or_create_learner(session)
    client = request.client.host if request.client else "unknown"
    if not auth.verify(user, body.passphrase, client):
        raise UnauthorizedError("Wrong passphrase")
    _start_session(response, user)


@router.post("/logout", status_code=204)
def logout(response: Response) -> None:
    response.delete_cookie(auth.COOKIE_NAME)


def _start_session(response: Response, user: User) -> None:
    settings = get_settings()
    response.set_cookie(
        auth.COOKIE_NAME,
        auth.issue_token(user),
        max_age=settings.session_days * 86400,
        httponly=True,
        samesite="strict",
        secure=settings.cookie_secure,
    )
