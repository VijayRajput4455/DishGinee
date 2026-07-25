from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class CuisineBase(BaseModel):
    """Base Pydantic DTO schema for Cuisine properties."""

    name: str = Field(..., min_length=2, max_length=100, description="Cuisine name (e.g. Indian, Italian)")
    code: str = Field(default="CUSTOM", max_length=10, description="Short cuisine code (e.g. IN, IT, MX)")
    description: Optional[str] = Field(default=None, description="Optional description of cuisine style")
    is_active: bool = Field(default=True, description="Active status indicator")


class CuisineCreate(CuisineBase):
    """Schema for creating a new Cuisine."""

    pass


class CuisineUpdate(BaseModel):
    """Schema for updating an existing Cuisine."""

    name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    code: Optional[str] = Field(default=None, max_length=10)
    description: Optional[str] = Field(default=None)
    is_active: Optional[bool] = Field(default=None)


class CuisineResponse(CuisineBase):
    """Response DTO schema for Cuisine entity."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Unique cuisine ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
