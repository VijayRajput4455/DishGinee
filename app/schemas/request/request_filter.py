from datetime import datetime

from pydantic import BaseModel, Field

from app.enums import InputType, RequestStatus


class RequestFilterParams(BaseModel):
    """Query parameters schema for filtering requests list."""

    input_type: InputType | None = Field(default=None, description="Filter by input type (IMAGE, TEXT, VOICE)")
    status: RequestStatus | None = Field(default=None, description="Filter by status (PENDING, PROCESSING, COMPLETED, FAILED)")
    date_from: datetime | None = Field(default=None, description="Filter requests created on or after this timestamp")
    date_to: datetime | None = Field(default=None, description="Filter requests created on or before this timestamp")
