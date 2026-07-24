from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.enums import ImageStatus


class ImageResponse(BaseModel):
    """Response DTO for RequestImage model."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Unique image record ID")
    request_id: int = Field(..., description="Associated request ID")
    original_image: str = Field(..., description="Storage URL/key of raw uploaded image")
    annotated_image: str | None = Field(default=None, description="Storage URL/key of YOLO annotated image")
    status: ImageStatus = Field(..., description="Processing status of the image")
    created_at: datetime = Field(..., description="Timestamp when image was uploaded")
    updated_at: datetime = Field(..., description="Timestamp when image was last updated")
