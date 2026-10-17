import secrets
from datetime import UTC, datetime, timedelta
from functools import lru_cache

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from itsdangerous import BadSignature, URLSafeTimedSerializer
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.errors import ForbiddenError, TooManyRequestsError
from app.models import LoginAttempt, User

COOKIE_NAME = "mf_session"
MIN_LENGTH = 8
MAX_ATTEMPTS = 5
WINDOW = timedelta(minutes=1)

_hasher = PasswordHasher()


@lru_cache
def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(_secret_key(), salt="session")


def _secret_key() -> str:
    """MF_SECRET_KEY if set; otherwise one generated once and kept with the media volume."""
    settings = get_settings()
    if settings.secret_key:
        return settings.secret_key
    path = settings.media_dir / ".secret_key"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(secrets.token_urlsafe(48))
        path.chmod(0o600)
    return path.read_text().strip()


def set_passphrase(session: Session, user: User, passphrase: str) -> None:
    if user.passphrase_hash is not None:
        raise ForbiddenError("A passphrase is already set")
    _store(session, user, passphrase)


def change_passphrase(session: Session, user: User, current: str, new: str, client: str) -> None:
    if not verify(session, user, current, client):
        raise ForbiddenError("The current passphrase is wrong")
    _store(session, user, new)
    sign_out_everywhere(session, user)


def sign_out_everywhere(session: Session, user: User) -> None:
    user.session_version += 1
    session.commit()


def check_setup_code(session: Session, code: str, client: str) -> None:
    expected = get_settings().setup_code
    if expected is None:
        return
    _throttle(session, client)
    if not secrets.compare_digest(code.encode(), expected.encode()):
        raise ForbiddenError("Wrong setup code")


def verify(session: Session, user: User, passphrase: str, client: str) -> bool:
    _throttle(session, client)
    if user.passphrase_hash is None:
        return False
    try:
        _hasher.verify(user.passphrase_hash, passphrase)
    except VerifyMismatchError:
        return False
    # Hashes made with older, weaker Argon2 settings are upgraded on the next sign-in.
    if _hasher.check_needs_rehash(user.passphrase_hash):
        _store(session, user, passphrase)
    return True


def issue_token(user: User) -> str:
    return _serializer().dumps({"uid": user.id, "v": user.session_version})


def user_from(session: Session, token: str | None) -> User | None:
    if not token:
        return None
    max_age = get_settings().session_days * 86400
    try:
        data = _serializer().loads(token, max_age=max_age)
    except BadSignature:
        return None
    user = session.get(User, int(data["uid"]))
    if user is None or data.get("v") != user.session_version:
        return None
    return user


def _store(session: Session, user: User, passphrase: str) -> None:
    if len(passphrase) < MIN_LENGTH:
        raise ForbiddenError(f"Use at least {MIN_LENGTH} characters")
    user.passphrase_hash = _hasher.hash(passphrase)
    session.commit()


def _throttle(session: Session, client: str) -> None:
    since = datetime.now(UTC) - WINDOW
    session.execute(delete(LoginAttempt).where(LoginAttempt.created_at < since))
    recent = session.scalar(
        select(func.count()).select_from(LoginAttempt).where(LoginAttempt.client == client)
    )
    if recent is not None and recent >= MAX_ATTEMPTS:
        session.commit()
        raise TooManyRequestsError("Too many attempts; wait a minute")
    session.add(LoginAttempt(client=client[:64]))
    # Committed before the passphrase is checked, so a failed sign-in still counts.
    session.commit()
