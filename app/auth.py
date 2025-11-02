from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.rate_limiter import get_client_ip, rate_limit
from app.security.authorization import AuthUser, require_auth
from app.security.jwt import (
    TokenError,
    issue_access_token,
    issue_refresh_token,
    revoke_refresh_token,
    verify_token,
)

router = APIRouter(prefix="/auth", tags=["authentication"])


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


_demo_users = {
    "demo": {"password": "demo123", "user_id": "demo-user", "role": "user"},
    "admin": {"password": "admin123", "user_id": "admin-user", "role": "admin"},
}


@router.post("/login", response_model=TokenResponse)
async def login(request: Request, credentials: LoginRequest):
    await rate_limit(request, get_client_ip(request), max_requests=5, window_minutes=1)

    user = _demo_users.get(credentials.username)
    if not user or user["password"] != credentials.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = issue_access_token(sub=user["user_id"], role=user["role"])
    refresh_token = issue_refresh_token(sub=user["user_id"])

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/token", response_model=TokenResponse)
async def refresh_access_token(request: Request, refresh_req: RefreshRequest):
    try:
        payload = verify_token(refresh_req.refresh_token, token_type="refresh")
        sub = payload.get("sub")

        if not sub:
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        identifier = f"{sub}:{get_client_ip(request)}"
        await rate_limit(request, identifier, max_requests=5, window_minutes=1)

        role = "user"
        for user_data in _demo_users.values():
            if user_data["user_id"] == sub:
                role = user_data["role"]
                break

        access_token = issue_access_token(sub=sub, role=role)
        new_refresh_token = issue_refresh_token(sub=sub)

        old_jti = payload.get("jti")
        if old_jti:
            revoke_refresh_token(old_jti)

        return TokenResponse(access_token=access_token, refresh_token=new_refresh_token)
    except TokenError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/logout")
async def logout(refresh_req: RefreshRequest, user: AuthUser = Depends(require_auth)):
    try:
        payload = verify_token(refresh_req.refresh_token, token_type="refresh")
        jti = payload.get("jti")
        if jti:
            revoke_refresh_token(jti)
        return {"message": "Logged out successfully"}
    except TokenError:
        return {"message": "Already logged out or invalid token"}
