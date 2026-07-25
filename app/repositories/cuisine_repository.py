from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.cuisine import Cuisine
from app.repositories.base_repository import BaseRepository


class CuisineRepository(BaseRepository[Cuisine]):
    """Repository for managing Cuisine database operations."""

    DEFAULT_CUISINES = [
        {"name": "Indian", "emoji": "🇮🇳", "code": "IN", "description": "Rich aromatic curries, gravies, biryanis & spicy masalas."},
        {"name": "Italian", "emoji": "🇮🇹", "code": "IT", "description": "Authentic hand-tossed pizzas, creamy pastas, & risottos."},
        {"name": "Mexican", "emoji": "🇲🇽", "code": "MX", "description": "Flavorful tacos, cheesy quesadillas, burritos & salsas."},
        {"name": "Asian", "emoji": "⛩️", "code": "AS", "description": "Dim sums, stir-fried noodles, ramen & savoury broths."},
        {"name": "French", "emoji": "🇫🇷", "code": "FR", "description": "Gourmet buttery pastries, bisques, soufflés & stews."},
        {"name": "Mediterranean", "emoji": "🌴", "code": "MD", "description": "Healthy olive oil roasts, hummus, falafel & grilled seafood."},
        {"name": "Japanese", "emoji": "🇯🇵", "code": "JP", "description": "Fresh sushi rolls, teriyaki grills, tempura & miso bowls."},
        {"name": "Thai", "emoji": "🇹🇭", "code": "TH", "description": "Spicy aromatic green curries, pad thai & lemongrass soups."},
    ]

    def __init__(self, db: Session) -> None:
        super().__init__(Cuisine, db)

    def seed_defaults_if_empty(self) -> list[Cuisine]:
        """Automatically seed initial cuisines if database table is empty."""
        existing = self.get_all()
        if not existing:
            for item in self.DEFAULT_CUISINES:
                obj = Cuisine(
                    name=item["name"],
                    emoji=item["emoji"],
                    code=item["code"],
                    description=item["description"],
                    is_active=True,
                )
                self.db.add(obj)
            self.db.commit()
            return self.get_all()
        return existing

    def get_all_active(self) -> list[Cuisine]:
        """Fetch all active cuisines from database."""
        self.seed_defaults_if_empty()
        stmt = select(Cuisine).where(Cuisine.is_active == True).order_by(Cuisine.id)
        return list(self.db.execute(stmt).scalars().all())

    def get_by_name(self, name: str) -> Optional[Cuisine]:
        """Fetch a cuisine by its unique name."""
        stmt = select(Cuisine).where(Cuisine.name.ilike(name))
        return self.db.execute(stmt).scalar_one_or_none()
