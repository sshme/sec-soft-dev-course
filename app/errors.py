from typing import Any, Dict, Optional
from uuid import uuid4

from starlette.responses import JSONResponse

from app.middleware import get_correlation_id


def problem(
    status: int,
    title: str,
    detail: str,
    type_: str = "about:blank",
    instance: Optional[str] = None,
    extras: Optional[Dict[str, Any]] = None,
) -> JSONResponse:
    correlation_id = get_correlation_id() or str(uuid4())
    payload = {
        "type": type_,
        "title": title,
        "status": status,
        "detail": detail,
        "correlation_id": correlation_id,
    }

    if instance:
        payload["instance"] = instance

    if extras:
        payload.update(extras)

    return JSONResponse(
        payload, status_code=status, media_type="application/problem+json"
    )
