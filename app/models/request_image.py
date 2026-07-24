from sqlalchemy import Enum as SQLEnum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.enums import ImageStatus
from app.models.base_model import BaseModel


class RequestImage(BaseModel):
    __tablename__ = "request_images"

    request_id: Mapped[int] = mapped_column(
        ForeignKey("requests.id", ondelete="CASCADE"),
        nullable=False,
    )

    original_image: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    annotated_image: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    status: Mapped[ImageStatus] = mapped_column(
        SQLEnum(ImageStatus),
        default=ImageStatus.UPLOADED,
        nullable=False,
    )

    request = relationship(
        "Request",
        back_populates="images",
    )