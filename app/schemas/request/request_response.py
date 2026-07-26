from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.enums import InputType, RequestStatus
from app.schemas.image.image_response import ImageResponse
from app.schemas.recipe.recipe_response import RequestOutputResponse


class RequestResponse(BaseModel):
    """Response DTO for basic Request metadata."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Unique request ID")
    input_type: InputType = Field(..., description="Input method used (IMAGE, TEXT, VOICE)")
    status: RequestStatus = Field(..., description="Current processing status")
    cuisine: str | None = Field(default=None, description="Optional target cuisine preference")
    is_vegetarian: bool | None = Field(default=None, description="Dietary preference constraint (true=Veg, false=Non-Veg, null=Any)")
    raw_text_input: str | None = Field(default=None, description="Raw text ingredient list if TEXT input")
    audio_url: str | None = Field(default=None, description="Audio storage URL if VOICE input")
    audio_transcription: str | None = Field(default=None, description="Transcribed audio text if VOICE input")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class RequestDetailResponse(RequestResponse):
    """Complete detail response DTO including nested images and outputs."""

    images: list[ImageResponse] = Field(default_factory=list, description="Associated uploaded images metadata")
    output: RequestOutputResponse | None = Field(default=None, description="Associated processing output and recipe guides")
