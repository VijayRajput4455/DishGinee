from pydantic import BaseModel, Field


class RecipeSelectRequest(BaseModel):
    """Payload schema when a user selects a recipe option from Stage 1 recommendations."""

    recipe_title: str = Field(..., description="Title of the selected candidate recipe")
    recipe_index: int | None = Field(default=None, ge=0, description="Optional zero-based index of the chosen recipe option")


class DirectRecipeGuideRequest(BaseModel):
    """Payload schema to request a direct cooking guide by dish name."""

    recipe_title: str = Field(..., min_length=2, description="Exact dish or recipe name e.g. Paneer Butter Masala")
    cuisine: str | None = Field(default=None, description="Optional target cuisine style")
    is_vegetarian: bool | None = Field(default=None, description="Dietary constraint (true=Veg, false=Non-Veg, null=Any)")
