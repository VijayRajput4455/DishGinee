from pydantic import BaseModel, Field


class RecipeSelectRequest(BaseModel):
    """Payload schema when a user selects a recipe option from Stage 1 recommendations."""

    recipe_title: str = Field(..., description="Title of the selected candidate recipe")
    recipe_index: int | None = Field(default=None, ge=0, description="Optional zero-based index of the chosen recipe option")
