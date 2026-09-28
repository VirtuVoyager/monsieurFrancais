from typing import Annotated

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionDep
from app.models import User

DEFAULT_SETTINGS = {"target_nclc": 7, "daily_minutes": 90, "timezone": "Asia/Kolkata"}


def get_or_create_learner(session: Session) -> User:
    user = session.scalar(select(User).order_by(User.id).limit(1))
    if user is None:
        user = User(display_name="Learner", passphrase_hash=None, settings=dict(DEFAULT_SETTINGS))
        session.add(user)
        session.commit()
    return user


def current_user(session: SessionDep) -> User:
    # Single-learner app: the passphrase gate (phase 1 auth) sits in front of this.
    return get_or_create_learner(session)


CurrentUser = Annotated[User, Depends(current_user)]
