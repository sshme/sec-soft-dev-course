from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, Tuple

from fastapi import HTTPException, Request


class RateLimiter:
    def __init__(self):
        self._requests: Dict[Tuple[str, str], list[datetime]] = defaultdict(list)

    def check_limit(
        self, identifier: str, endpoint: str, max_requests: int, window: timedelta
    ) -> bool:
        key = (identifier, endpoint)
        now = datetime.now()
        cutoff = now - window

        self._requests[key] = [ts for ts in self._requests[key] if ts > cutoff]

        if len(self._requests[key]) >= max_requests:
            return False

        self._requests[key].append(now)
        return True

    def cleanup_old_entries(self, max_age: timedelta = timedelta(hours=1)):
        now = datetime.now()
        cutoff = now - max_age
        keys_to_delete = []
        for key, timestamps in self._requests.items():
            self._requests[key] = [ts for ts in timestamps if ts > cutoff]
            if not self._requests[key]:
                keys_to_delete.append(key)
        for key in keys_to_delete:
            del self._requests[key]


rate_limiter = RateLimiter()


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def rate_limit(
    request: Request, identifier: str, max_requests: int, window_minutes: int
):
    endpoint = request.url.path
    if not rate_limiter.check_limit(
        identifier, endpoint, max_requests, timedelta(minutes=window_minutes)
    ):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
