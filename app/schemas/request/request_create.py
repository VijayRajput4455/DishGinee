from pydantic import BaseModel, Field


class RequestCreateText(BaseModel):
    """Payload schema for submitting raw text ingredient input."""

    raw_text_input: str = Field(..., min_length=3, description="Comma-separated or free-form ingredient list")


class RequestCreateVoice(BaseModel):
    """Payload schema for submitting voice audio recording input."""

    audio_url: str = Field(..., description="MinIO storage URL or key for the uploaded voice audio file")
