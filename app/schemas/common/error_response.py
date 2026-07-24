from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Specific field-level validation error detail."""

    field: str | None = Field(default=None, description="Field path causing the error")
    message: str = Field(..., description="Error message")


class ErrorResponse(BaseModel):
    """Standardized API error response payload."""

    success: bool = Field(default=False, description="Always False for error responses")
    error: str = Field(..., description="Error code or high-level error summary")
    details: list[ErrorDetail] | None = Field(default=None, description="Detailed validation errors")
