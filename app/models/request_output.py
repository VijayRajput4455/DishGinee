from typing import Any

from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base_model import BaseModel


class RequestOutput(BaseModel):
    __tablename__ = "request_outputs"

    request_id: Mapped[int] = mapped_column(
        ForeignKey("requests.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    ingredients: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    selected_recipe: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    cooking_guide: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    request = relationship(
        "Request",
        back_populates="output",
    )