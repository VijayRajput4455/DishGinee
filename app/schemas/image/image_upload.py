from pydantic import BaseModel, Field


class ImageUploadRequest(BaseModel):
    """Payload metadata when initiating an image upload."""

    filename: str = Field(..., description="Original name of the uploaded image file")
    content_type: str = Field(..., description="MIME type of the image (e.g., image/jpeg, image/png)")
    file_size_bytes: int | None = Field(default=None, description="Size of image file in bytes")
