from pydantic import BaseModel, Field

from app.enums import RequestStatus


class RequestUpdateStatus(BaseModel):
    """Payload schema for updating request execution status."""

    status: RequestStatus = Field(..., description="Target status (PENDING, PROCESSING, COMPLETED, FAILED)")
