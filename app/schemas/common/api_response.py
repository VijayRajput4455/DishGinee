from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """Standardized API response wrapper for DishGenie endpoints."""

    success: bool = Field(default=True, description="Indicates if operation succeeded")
    message: str = Field(default="Operation completed successfully", description="Status message")
    data: T | None = Field(default=None, description="Response payload")
