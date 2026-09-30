import secrets
import time
from collections import defaultdict, deque
from functools import lru_cache

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from itsdangerous import BadSignature, URLSafeTimedSerializer
from sqlalchemy.orm import Session

from app.config import get_settings
from app.errors import ForbiddenError, TooManyRequestsError
from app.models import User

COOKIE_NAME = "mf_session"
MIN_LENGTH = 8
MAX_ATTEMPTS = 5
WINDOW_SECONDS = 60.0

_hasher = PasswordHasher()
_attempts: defaultdict[str, deque[float]] = defaultdict(deque)


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
    if len(passphrase) < MIN_LENGTH:
        raise ForbiddenError(f"Use at least {MIN_LENGTH} characters")
    user.passphrase_hash = _hasher.hash(passphrase)
    session.commit()


def verify(user: User, passphrase: str, client: str) -> bool:
    _throttle(client)
    if user.passphrase_hash is None:
        return False
    try:
        return _hasher.verify(user.passphrase_hash, passphrase)
    except VerifyMismatchError:
        return False


def issue_token(user: User) -> str:
    return _serializer().dumps({"uid": user.id})


def user_id_from(token: str | None) -> int | None:
    if not token:
        return None
    max_age = get_settings().session_days * 86400
    try:
        data = _serializer().loads(token, max_age=max_age)
    except BadSignature:
        return None
    return int(data["uid"])


def _throttle(client: str) -> None:
    now = time.monotonic()
    attempts = _attempts[client]
    while attempts and now - attempts[0] > WINDOW_SECONDS:
        attempts.popleft()
    if len(attempts) >= MAX_ATTEMPTS:
        raise TooManyRequestsError("Too many attempts; wait a minute")
    attempts.append(now)
