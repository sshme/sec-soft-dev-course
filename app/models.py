from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class HighlightCreate(BaseModel):
    """Model for creating a new highlight"""

    text: str = Field(
        ..., min_length=1, max_length=2000, description="The highlighted text/quote"
    )
    source: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Source of the highlight (book, article, etc.)",
    )
    tags: List[str] = Field(
        default=[], description="Tags for categorizing the highlight"
    )

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v):
        if len(v) > 10:
            raise ValueError("Maximum 10 tags allowed")
        return [tag.strip().lower() for tag in v if tag.strip()]


class HighlightUpdate(BaseModel):
    """Model for updating an existing highlight"""

    text: Optional[str] = Field(None, min_length=1, max_length=2000)
    source: Optional[str] = Field(None, min_length=1, max_length=500)
    tags: Optional[List[str]] = Field(None)

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v):
        if v is None:
            return v
        if len(v) > 10:
            raise ValueError("Maximum 10 tags allowed")
        return [tag.strip().lower() for tag in v if tag.strip()]


class Highlight(BaseModel):
    """Model representing a complete highlight"""

    id: int
    text: str
    source: str
    tags: List[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class HighlightResponse(BaseModel):
    """Response model for highlight operations"""

    highlight: Highlight
    message: str = "Success"


class HighlightListResponse(BaseModel):
    """Response model for listing highlights"""

    highlights: List[Highlight]
    total: int
    message: str = "Success"
