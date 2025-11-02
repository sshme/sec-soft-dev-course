from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError

from app.auth import router as auth_router
from app.errors import problem
from app.markdown_builder import HighlightsMarkdownExporter
from app.middleware import CorrelationIdMiddleware
from app.models import (
    Highlight,
    HighlightCreate,
    HighlightListResponse,
    HighlightResponse,
    HighlightUpdate,
)
from app.rate_limiter import get_client_ip, rate_limit
from app.security.authorization import AuthUser, require_auth, require_owner
from app.storage import storage

app = FastAPI(
    title="Reading Highlights API",
    version="1.0.0",
    description="API for managing reading highlights and quotes",
)

app.add_middleware(CorrelationIdMiddleware)
app.include_router(auth_router)


class ApiError(Exception):
    def __init__(self, code: str, message: str, status: int = 400):
        self.code = code
        self.message = message
        self.status = status


@app.exception_handler(ApiError)
async def api_error_handler(request: Request, exc: ApiError):
    return problem(
        status=exc.status,
        title=exc.code.replace("_", " ").title(),
        detail=exc.message,
        type_=f"/errors/{exc.code.replace('_', '-')}",
        instance=str(request.url),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail if isinstance(exc.detail, str) else "HTTP error occurred"
    return problem(
        status=exc.status_code,
        title="HTTP Error",
        detail=detail,
        type_="/errors/http-error",
        instance=str(request.url),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    serializable_errors = []
    for error in errors:
        error_dict = {
            "loc": error.get("loc", []),
            "msg": error.get("msg", ""),
            "type": error.get("type", ""),
        }
        if "input" in error:
            error_dict["input"] = error["input"]
        serializable_errors.append(error_dict)

    detail = f"Validation failed: {len(errors)} error(s)"
    return problem(
        status=422,
        title="Validation Error",
        detail=detail,
        type_="/errors/validation",
        instance=str(request.url),
        extras={"validation_errors": serializable_errors},
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/highlights", response_model=HighlightResponse, status_code=201)
async def create_highlight(
    request: Request,
    highlight_data: HighlightCreate,
    user: AuthUser = Depends(require_auth),
):
    await rate_limit(request, get_client_ip(request), max_requests=10, window_minutes=1)

    new_highlight = storage.create(
        text=highlight_data.text,
        source=highlight_data.source,
        tags=highlight_data.tags,
        owner_id=user.sub,
    )

    return HighlightResponse(
        highlight=Highlight(**new_highlight), message="Highlight created successfully"
    )


@app.get("/highlights", response_model=HighlightListResponse)
def get_highlights(
    tag: Optional[str] = Query(None, description="Filter by tag"),
    user: AuthUser = Depends(require_auth),
):
    if tag:
        highlights = storage.get_by_tag(tag, owner_id=user.sub)
    else:
        highlights = storage.get_all(owner_id=user.sub)

    highlights.sort(key=lambda x: x["created_at"], reverse=True)

    return HighlightListResponse(
        highlights=[Highlight(**h) for h in highlights],
        total=len(highlights),
        message="Highlights retrieved successfully",
    )


@app.get("/highlights/{highlight_id}", response_model=HighlightResponse)
def get_highlight(highlight_id: int, user: AuthUser = Depends(require_auth)):
    if user.is_admin():
        highlight = storage.get_by_id(highlight_id)
    else:
        highlight = storage.get_by_id(highlight_id, owner_id=user.sub)

    if not highlight:
        raise ApiError(
            code="not_found",
            message=f"Highlight with ID {highlight_id} not found",
            status=404,
        )

    if not user.is_admin():
        require_owner(highlight["owner_id"], user)

    return HighlightResponse(
        highlight=Highlight(**highlight), message="Highlight retrieved successfully"
    )


@app.put("/highlights/{highlight_id}", response_model=HighlightResponse)
def update_highlight(
    highlight_id: int,
    highlight_data: HighlightUpdate,
    user: AuthUser = Depends(require_auth),
):
    update_data = highlight_data.model_dump(exclude_unset=True)

    updated_highlight = storage.update(highlight_id, update_data, owner_id=user.sub)

    if not updated_highlight:
        raise ApiError(
            code="not_found",
            message=f"Highlight with ID {highlight_id} not found",
            status=404,
        )

    return HighlightResponse(
        highlight=Highlight(**updated_highlight),
        message="Highlight updated successfully",
    )


@app.delete("/highlights/{highlight_id}")
def delete_highlight(highlight_id: int, user: AuthUser = Depends(require_auth)):
    deleted_highlight = storage.delete(highlight_id, owner_id=user.sub)

    if not deleted_highlight:
        raise ApiError(
            code="not_found",
            message=f"Highlight with ID {highlight_id} not found",
            status=404,
        )

    return {
        "message": "Highlight deleted successfully",
        "deleted_id": highlight_id,
        "deleted_text": (
            deleted_highlight["text"][:50] + "..."
            if len(deleted_highlight["text"]) > 50
            else deleted_highlight["text"]
        ),
    }


@app.get("/highlights/export/markdown")
def export_highlights_markdown(
    tag: Optional[str] = Query(None, description="Filter by tag"),
    user: AuthUser = Depends(require_auth),
):
    if tag:
        highlights = storage.get_by_tag(tag, owner_id=user.sub)
    else:
        highlights = storage.get_all(owner_id=user.sub)

    markdown_content, total = HighlightsMarkdownExporter.export(
        highlights, filter_tag=tag
    )

    return {
        "message": "Markdown export generated successfully",
        "content": markdown_content,
        "total_highlights": total,
    }
