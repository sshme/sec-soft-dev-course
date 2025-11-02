from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

import jwt

from app.config import config

ACCESS_TOKEN_TTL = timedelta(minutes=15)
REFRESH_TOKEN_TTL = timedelta(days=7)
CLOCK_SKEW = timedelta(seconds=60)
ALGORITHM = "HS256"
ISSUER = "reading-highlights-api"
AUDIENCE = "reading-highlights-api"

_refresh_denylist: set[str] = set()


class TokenError(Exception):
    pass


def _get_signing_key() -> str:
    if not config.secret_key:
        raise RuntimeError("SECRET_KEY not configured")
    return config.secret_key


def _get_previous_key() -> Optional[str]:
    return config.secret_key_prev


def issue_access_token(
    sub: str, role: str = "user", scopes: Optional[list[str]] = None
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "sub": sub,
        "iat": now,
        "exp": now + ACCESS_TOKEN_TTL,
        "jti": str(uuid4()),
        "role": role,
    }
    if scopes:
        payload["scopes"] = scopes
    return jwt.encode(payload, _get_signing_key(), algorithm=ALGORITHM)


def issue_refresh_token(sub: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "sub": sub,
        "iat": now,
        "exp": now + REFRESH_TOKEN_TTL,
        "jti": str(uuid4()),
        "type": "refresh",
    }
    return jwt.encode(payload, _get_signing_key(), algorithm=ALGORITHM)


def verify_token(token: str, token_type: str = "access") -> dict:
    keys_to_try = [_get_signing_key()]
    prev_key = _get_previous_key()
    if prev_key:
        keys_to_try.append(prev_key)

    for key in keys_to_try:
        try:
            payload = jwt.decode(
                token,
                key,
                algorithms=[ALGORITHM],
                issuer=ISSUER,
                audience=AUDIENCE,
                leeway=CLOCK_SKEW.total_seconds(),
            )

            if token_type == "refresh":
                if payload.get("type") != "refresh":
                    raise TokenError("invalid_token_type")
                jti = payload.get("jti")
                if jti and jti in _refresh_denylist:
                    raise TokenError("token_revoked")

            return payload
        except jwt.ExpiredSignatureError:
            raise TokenError("token_expired")
        except jwt.InvalidTokenError:
            continue

    raise TokenError("invalid_token")


def revoke_refresh_token(jti: str) -> None:
    _refresh_denylist.add(jti)


def clear_denylist() -> None:
    _refresh_denylist.clear()
