from contextvars import ContextVar
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        correlation_id = str(uuid4())
        correlation_id_var.set(correlation_id)

        request.state.correlation_id = correlation_id

        response = await call_next(request)
        response.headers["X-Correlation-Id"] = correlation_id

        return response


def get_correlation_id() -> str:
    return correlation_id_var.get()
