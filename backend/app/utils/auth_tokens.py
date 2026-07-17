from datetime import datetime, timedelta, timezone

import jwt

from ..config import get_settings

ALGORITHM = "HS256"


def create_access_token(claims: dict, expires_minutes: int | None = None) -> str:
    settings = get_settings()
    exp = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes or settings.token_expire_minutes
    )
    return jwt.encode(claims | {"exp": exp}, settings.app_secret, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Returns the claims dict. Raises jwt.InvalidTokenError on any failure
    (bad signature, expired, malformed)."""
    settings = get_settings()
    return jwt.decode(token, settings.app_secret, algorithms=[ALGORITHM])
