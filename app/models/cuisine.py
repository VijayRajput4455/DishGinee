from typing import Optional

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base_model import BaseModel


class Cuisine(BaseModel):
    """SQLAlchemy model representing a culinary style (e.g. Indian, Italian, Mexican)."""

    __tablename__ = "cuisines"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(10), nullable=False, default="CUSTOM")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<Cuisine id={self.id} name='{self.name}' code='{self.code}' active={self.is_active}>"
