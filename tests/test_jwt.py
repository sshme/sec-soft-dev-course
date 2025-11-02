from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.config import config
from app.security.jwt import (
    ACCESS_TOKEN_TTL,
    ALGORITHM,
    AUDIENCE,
    ISSUER,
    TokenError,
    clear_denylist,
    issue_access_token,
    issue_refresh_token,
    revoke_refresh_token,
    verify_token,
)


@pytest.fixture(autouse=True)
def setup_secret():
    original = config.secret_key
    config.secret_key = "test-secret-key-for-jwt-testing"
    config.secret_key_prev = None
    clear_denylist()
    yield
    config.secret_key = original
    config.secret_key_prev = None
    clear_denylist()


def test_issue_access_token():
    token = issue_access_token(sub="user-123", role="user")
    assert token
    assert isinstance(token, str)

    payload = jwt.decode(
        token, config.secret_key, algorithms=[ALGORITHM], audience=AUDIENCE
    )
    assert payload["sub"] == "user-123"
    assert payload["role"] == "user"
    assert payload["iss"] == ISSUER
    assert payload["aud"] == AUDIENCE
    assert "jti" in payload


def test_issue_refresh_token():
    token = issue_refresh_token(sub="user-456")
    assert token

    payload = jwt.decode(
        token, config.secret_key, algorithms=[ALGORITHM], audience=AUDIENCE
    )
    assert payload["sub"] == "user-456"
    assert payload["type"] == "refresh"
    assert "jti" in payload


def test_verify_access_token_success():
    token = issue_access_token(sub="user-789", role="admin")
    payload = verify_token(token, token_type="access")

    assert payload["sub"] == "user-789"
    assert payload["role"] == "admin"


def test_verify_refresh_token_success():
    token = issue_refresh_token(sub="user-101")
    payload = verify_token(token, token_type="refresh")

    assert payload["sub"] == "user-101"
    assert payload["type"] == "refresh"


def test_verify_expired_token():
    now = datetime.now(timezone.utc)
    expired_payload = {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "sub": "user-expired",
        "iat": now - timedelta(hours=1),
        "exp": now - timedelta(minutes=1),
        "jti": "expired-jti",
    }
    expired_token = jwt.encode(expired_payload, config.secret_key, algorithm=ALGORITHM)

    with pytest.raises(TokenError, match="token_expired"):
        verify_token(expired_token)


def test_verify_invalid_signature():
    token = issue_access_token(sub="user-123")
    tampered = token[:-10] + "tampered00"

    with pytest.raises(TokenError, match="invalid_token"):
        verify_token(tampered)


def test_key_rotation():
    config.secret_key = "new-key"
    config.secret_key_prev = "test-secret-key-for-jwt-testing"

    old_token = jwt.encode(
        {
            "iss": ISSUER,
            "aud": AUDIENCE,
            "sub": "user-old",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + ACCESS_TOKEN_TTL,
            "jti": "old-jti",
        },
        "test-secret-key-for-jwt-testing",
        algorithm=ALGORITHM,
    )

    payload = verify_token(old_token)
    assert payload["sub"] == "user-old"


def test_refresh_token_revocation():
    token = issue_refresh_token(sub="user-revoke")
    payload = verify_token(token, token_type="refresh")
    jti = payload["jti"]

    revoke_refresh_token(jti)

    with pytest.raises(TokenError, match="token_revoked"):
        verify_token(token, token_type="refresh")


def test_wrong_token_type():
    access_token = issue_access_token(sub="user-access")

    with pytest.raises(TokenError, match="invalid_token_type"):
        verify_token(access_token, token_type="refresh")


def test_access_token_with_scopes():
    token = issue_access_token(sub="user-scoped", role="user", scopes=["read", "write"])
    payload = verify_token(token)

    assert payload["scopes"] == ["read", "write"]
