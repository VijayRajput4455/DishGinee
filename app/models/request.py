from sqlalchemy import Enum as SQLEnum, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums import InputType, RequestStatus
from app.models.base_model import BaseModel


class Request(BaseModel):
    __tablename__ = "requests"

    input_type: Mapped[InputType] = mapped_column(
        SQLEnum(InputType),
        nullable=False,
    )

    status: Mapped[RequestStatus] = mapped_column(
        SQLEnum(RequestStatus),
        default=RequestStatus.PENDING,
        nullable=False,
    )

    cuisine: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    # Optional fields based on input_type (TEXT / VOICE)
    raw_text_input: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    audio_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    audio_transcription: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    images = relationship(
        "RequestImage",
        back_populates="request",
        cascade="all, delete-orphan",
    )

    output = relationship(
        "RequestOutput",
        back_populates="request",
        uselist=False,
        cascade="all, delete-orphan",
    )