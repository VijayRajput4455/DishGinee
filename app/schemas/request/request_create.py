from pydantic import BaseModel, Field


class RequestCreateText(BaseModel):
    """Payload schema for submitting raw text ingredient input."""

    raw_text_input: str = Field(..., min_length=3, description="Comma-separated or free-form ingredient list")
    cuisine: str | None = Field(default=None, description="Optional cuisine preference (e.g., Indian, Italian, Mexican, Asian)")
    is_vegetarian: bool | None = Field(default=None, description="Dietary preference constraint (true=Veg, false=Non-Veg, null=Any)")
    num_recipes: int = Field(default=5, ge=1, le=20, description="Number of recipe candidates requested")


class RequestCreateVoice(BaseModel):
    """Payload schema for submitting voice audio recording input."""

    audio_url: str = Field(..., description="MinIO storage URL or key for the uploaded voice audio file")
    cuisine: str | None = Field(default=None, description="Optional cuisine preference (e.g., Indian, Italian, Mexican, Asian)")
    is_vegetarian: bool | None = Field(default=None, description="Dietary preference constraint (true=Veg, false=Non-Veg, null=Any)")
    num_recipes: int = Field(default=5, ge=1, le=20, description="Number of recipe candidates requested")
