from typing import Annotated

from fastapi import Cookie, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionDep
from app.errors import UnauthorizedError
from app.models import User
from app.services.auth import COOKIE_NAME, user_from

DEFAULT_SETTINGS = {"target_nclc": 7, "daily_minutes": 90, "timezone": "Asia/Kolkata"}


def get_or_create_learner(session: Session) -> User:
    user = session.scalar(select(User).order_by(User.id).limit(1))
    if user is None:
        user = User(display_name="Learner", passphrase_hash=None, settings=dict(DEFAULT_SETTINGS))
        session.add(user)
        session.commit()
    return user


def current_user(
    session: SessionDep, token: Annotated[str | None, Cookie(alias=COOKIE_NAME)] = None
) -> User:
    user = user_from(session, token)
    if user is None:
        raise UnauthorizedError("Sign in first")
    return user


CurrentUser = Annotated[User, Depends(current_user)]
