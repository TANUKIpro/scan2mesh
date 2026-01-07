"""Profile model for managing scan projects."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class Profile(BaseModel):
    """A profile groups related scan objects together."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate profile name for path safety."""
        if ".." in v or "/" in v or "\\" in v:
            raise ValueError("Invalid characters in name")
        return v

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str]) -> list[str]:
        """Validate tag constraints."""
        if len(v) > 20:
            raise ValueError("Maximum 20 tags allowed")
        for tag in v:
            if len(tag) > 50:
                raise ValueError("Tag too long (max 50 characters)")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "RoboCup 2025 Objects",
                "description": "Objects for RoboCup 2025 competition",
                "tags": ["robocup", "2025"],
                "created_at": "2026-01-06T10:00:00",
                "updated_at": "2026-01-06T10:00:00",
            }
        }
    }
