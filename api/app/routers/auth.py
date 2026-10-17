from typing import Annotated

from fastapi import APIRouter, Cookie, Request, Response

from app.config import get_settings
from app.db import SessionDep
from app.errors import UnauthorizedError
from app.models import User
from app.schemas.auth import AuthStatus, NewPassphrase, Passphrase, Setup
from app.services import auth
from app.services.users import CurrentUser, get_or_create_learner

router = APIRouter(prefix="/auth", tags=["auth"])
SessionCookie = Annotated[str | None, Cookie(alias=auth.COOKIE_NAME)]


@router.get("/status")
def status(session: SessionDep, token: SessionCookie = None) -> AuthStatus:
    user = get_or_create_learner(session)
    return AuthStatus(
        configured=user.passphrase_hash is not None,
        authenticated=auth.user_from(session, token) is not None,
        setup_code_required=get_settings().setup_code is not None,
    )


@router.post("/setup", status_code=204)
def setup(body: Setup, session: SessionDep, request: Request, response: Response) -> None:
    user = get_or_create_learner(session)
    auth.check_setup_code(session, body.setup_code, _client(request))
    auth.set_passphrase(session, user, body.passphrase)
    _start_session(response, user)


@router.post("/login", status_code=204)
def login(body: Passphrase, session: SessionDep, request: Request, response: Response) -> None:
    user = get_or_create_learner(session)
    if not auth.verify(session, user, body.passphrase, _client(request)):
        raise UnauthorizedError("Wrong passphrase")
    _start_session(response, user)


@router.post("/logout", status_code=204)
def logout(response: Response) -> None:
    response.delete_cookie(auth.COOKIE_NAME)


@router.post("/logout-everywhere", status_code=204)
def logout_everywhere(user: CurrentUser, session: SessionDep, response: Response) -> None:
    auth.sign_out_everywhere(session, user)
    response.delete_cookie(auth.COOKIE_NAME)


@router.post("/passphrase", status_code=204)
def change_passphrase(
    body: NewPassphrase,
    user: CurrentUser,
    session: SessionDep,
    request: Request,
    response: Response,
) -> None:
    auth.change_passphrase(session, user, body.current, body.new, _client(request))
    # Every other device is signed out; this one gets a fresh cookie and stays in.
    _start_session(response, user)


def _client(request: Request) -> str:
    return request.client.host if request.client else "unknown"


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
