from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.request_output import RequestOutput
from app.repositories.base_repository import BaseRepository


class RequestOutputRepository(BaseRepository[RequestOutput]):
    """Repository for managing RequestOutput database operations."""

    def __init__(self, db: Session) -> None:
        super().__init__(RequestOutput, db)

    def get_by_request_id(self, request_id: int) -> RequestOutput | None:
        """Fetch the RequestOutput associated with a request_id."""
        stmt = select(RequestOutput).where(RequestOutput.request_id == request_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def upsert_output(
        self,
        request_id: int,
        ingredients: dict[str, Any] | list[Any] | None = None,
        selected_recipe: dict[str, Any] | None = None,
        cooking_guide: dict[str, Any] | None = None,
    ) -> RequestOutput:
        """Create or update output payload (extracted ingredients, selected recipe, cooking guide)."""
        output_obj = self.get_by_request_id(request_id)

        if output_obj is None:
            output_obj = RequestOutput(
                request_id=request_id,
                ingredients=ingredients,
                selected_recipe=selected_recipe,
                cooking_guide=cooking_guide,
            )
            return self.create(output_obj)

        if ingredients is not None:
            output_obj.ingredients = ingredients
        if selected_recipe is not None:
            output_obj.selected_recipe = selected_recipe
        if cooking_guide is not None:
            output_obj.cooking_guide = cooking_guide

        return self.update(output_obj)
