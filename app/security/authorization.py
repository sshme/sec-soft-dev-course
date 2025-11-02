from typing import Optional

from fastapi import Depends, Header, HTTPException

from app.security.jwt import TokenError, verify_token


class AuthUser:
    def __init__(self, sub: str, role: str, scopes: list[str]):
        self.sub = sub
        self.role = role
        self.scopes = scopes

    def has_scope(self, scope: str) -> bool:
        return scope in self.scopes

    def is_admin(self) -> bool:
        return self.role == "admin"


async def require_auth(authorization: Optional[str] = Header(None)) -> AuthUser:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=401, detail="Invalid authorization header format"
        )

    token = parts[1]
    try:
        payload = verify_token(token, token_type="access")
        sub = payload.get("sub")
        role = payload.get("role", "user")
        scopes = payload.get("scopes", [])

        if not sub:
            raise HTTPException(status_code=401, detail="Invalid token payload")

        return AuthUser(sub=sub, role=role, scopes=scopes)
    except TokenError as e:
        raise HTTPException(status_code=401, detail=str(e))


def require_scopes(required_scopes: list[str]):
    async def dependency(user: AuthUser = Depends(require_auth)) -> AuthUser:
        for scope in required_scopes:
            if not user.has_scope(scope):
                raise HTTPException(
                    status_code=403, detail=f"Missing required scope: {scope}"
                )
        return user

    return dependency


def require_role(required_role: str):
    async def dependency(user: AuthUser = Depends(require_auth)) -> AuthUser:
        if user.role != required_role:
            raise HTTPException(
                status_code=403,
                detail=f"Required role: {required_role}, got: {user.role}",
            )
        return user

    return dependency


def require_owner(resource_owner_id: str, user: AuthUser):
    if user.is_admin():
        return True
    if user.sub != resource_owner_id:
        raise HTTPException(status_code=404, detail="Resource not found")
    return True
