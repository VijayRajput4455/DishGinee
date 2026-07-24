from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DetectedIngredient(BaseModel):
    """Schema for a single detected ingredient item."""

    name: str = Field(..., description="Normalized ingredient name")
    confidence: float | None = Field(default=None, description="YOLO detection confidence score (0.0 to 1.0)")
    category: str | None = Field(default=None, description="Ingredient category (e.g. vegetable, protein, dairy)")


class RecipeOption(BaseModel):
    """Schema for candidate recipe options returned by Stage 1 LLM."""

    title: str = Field(..., description="Recipe title")
    description: str = Field(..., description="Short recipe description")
    prep_time: str = Field(..., description="Estimated prep time")
    matched_ingredients: list[str] = Field(default_factory=list, description="Ingredients present in user input")
    missing_ingredients: list[str] = Field(default_factory=list, description="Optional extra ingredients needed")


class CookingGuideStep(BaseModel):
    """Schema for a single cooking instruction step."""

    step_number: int = Field(..., ge=1, description="Sequential step number")
    instruction: str = Field(..., description="Detailed step instruction")
    duration_minutes: int | None = Field(default=None, description="Optional step duration in minutes")
    equipment: list[str] | None = Field(default=None, description="Kitchen tools or equipment needed for this step")


class MacroNutrients(BaseModel):
    """Nutritional breakdown per serving."""

    calories: int | None = Field(default=None, description="Calories (kcal)")
    protein_g: float | None = Field(default=None, description="Protein in grams")
    carbs_g: float | None = Field(default=None, description="Carbohydrates in grams")
    fats_g: float | None = Field(default=None, description="Fats in grams")


class CookingGuide(BaseModel):
    """Complete Stage 2 LLM Cooking Guide output."""

    title: str = Field(..., description="Full recipe title")
    servings: int = Field(default=2, ge=1, description="Number of servings")
    prep_time: str = Field(..., description="Preparation time")
    cook_time: str = Field(..., description="Cooking time")
    ingredients: list[str] = Field(..., description="List of all required ingredients with quantities")
    steps: list[CookingGuideStep] = Field(..., description="Ordered step-by-step instructions")
    macros: MacroNutrients | None = Field(default=None, description="Nutritional information per serving")
    substitutions: list[str] | None = Field(default=None, description="Suggested ingredient substitutions")


class RequestOutputResponse(BaseModel):
    """Response DTO for RequestOutput model."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Output record ID")
    request_id: int = Field(..., description="Associated request ID")
    ingredients: dict[str, Any] | list[Any] | None = Field(default=None, description="Raw/extracted ingredients data")
    selected_recipe: dict[str, Any] | None = Field(default=None, description="Selected recipe summary payload")
    cooking_guide: dict[str, Any] | None = Field(default=None, description="Full generated cooking guide payload")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
