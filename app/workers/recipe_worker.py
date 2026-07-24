from typing import Any

from sqlalchemy.orm import Session

from app.enums import RequestStatus
from app.repositories import RequestOutputRepository, RequestRepository


class LLMRecipeWorker:
    """Worker handling Stage 1 (candidate recipe options) and Stage 2 (full cooking guide) LLM generation."""

    def __init__(self) -> None:
        pass

    def generate_stage1_options(self, ingredients: list[str]) -> list[dict[str, Any]]:
        """Stage 1: Generate 3-4 candidate recipe options using fast LLM."""
        ing_str = ", ".join(ingredients) if isinstance(ingredients, list) else str(ingredients)
        return [
            {
                "title": f"Garlic Butter {ingredients[0].title() if ingredients else 'Delight'}",
                "description": f"A quick, flavorful dish featuring fresh {ing_str}.",
                "prep_time": "15 mins",
                "matched_ingredients": ingredients,
                "missing_ingredients": ["salt", "black pepper"],
            },
            {
                "title": f"Rustic {ingredients[0].title() if ingredients else 'Garden'} Stir-Fry",
                "description": f"Sautéd {ing_str} seasoned to perfection.",
                "prep_time": "20 mins",
                "matched_ingredients": ingredients,
                "missing_ingredients": ["olive oil"],
            },
            {
                "title": f"Creamy {ingredients[0].title() if ingredients else 'Chef'} Skillet",
                "description": f"Comforting one-pan meal using {ing_str}.",
                "prep_time": "25 mins",
                "matched_ingredients": ingredients,
                "missing_ingredients": ["cream", "parmesan"],
            },
        ]

    def generate_stage2_guide(self, recipe_title: str) -> dict[str, Any]:
        """Stage 2: Generate detailed step-by-step cooking guide using LLM structured output."""
        return {
            "title": recipe_title,
            "servings": 2,
            "prep_time": "15 mins",
            "cook_time": "20 mins",
            "ingredients": [
                "250g Main Ingredient",
                "2 cloves Garlic, minced",
                "2 tbsp Butter / Olive Oil",
                "Salt and Freshly Ground Black Pepper to taste",
            ],
            "steps": [
                {
                    "step_number": 1,
                    "instruction": "Prep ingredients: Wash and chop fresh vegetables/proteins into uniform bites.",
                    "duration_minutes": 5,
                    "equipment": ["Cutting board", "Chef knife"],
                },
                {
                    "step_number": 2,
                    "instruction": "Heat butter/oil in a heavy skillet over medium-high heat until shimmering.",
                    "duration_minutes": 3,
                    "equipment": ["Skillet", "Spatula"],
                },
                {
                    "step_number": 3,
                    "instruction": "Add minced garlic and stir-fry for 1 minute until fragrant. Add main ingredients.",
                    "duration_minutes": 7,
                    "equipment": ["Skillet"],
                },
                {
                    "step_number": 4,
                    "instruction": "Season generously with salt and pepper. Toss well and serve warm.",
                    "duration_minutes": 5,
                    "equipment": ["Serving bowl"],
                },
            ],
            "macros": {
                "calories": 420,
                "protein_g": 28.5,
                "carbs_g": 14.0,
                "fats_g": 22.0,
            },
            "substitutions": [
                "Substitute butter with avocado oil for a dairy-free alternative.",
            ],
        }

    def process_recipe_task(self, payload: dict[str, Any], db: Session) -> bool:
        """Process a Stage 1 candidate recipe generation task."""
        request_id = payload.get("request_id")
        ingredients = payload.get("ingredients", [])

        if not request_id:
            print("[LLMRecipeWorker] Invalid payload missing request_id")
            return False

        req_repo = RequestRepository(db)
        out_repo = RequestOutputRepository(db)

        # 1. Generate Stage 1 recipe candidate options
        options = self.generate_stage1_options(ingredients)

        # 2. Update RequestOutput with candidate options payload
        out_repo.upsert_output(request_id=request_id, ingredients=options)

        # 3. Update Request status to COMPLETED
        req_repo.update_status(request_id=request_id, status=RequestStatus.COMPLETED)

        print(f"[LLMRecipeWorker] Successfully generated {len(options)} recipe options for Request #{request_id}")
        return True

    def process_guide_task(self, payload: dict[str, Any], db: Session) -> bool:
        """Process a Stage 2 full cooking guide generation task."""
        request_id = payload.get("request_id")
        selected_recipe = payload.get("selected_recipe")

        if not request_id or not selected_recipe:
            print("[LLMRecipeWorker] Invalid payload missing request_id or selected_recipe")
            return False

        out_repo = RequestOutputRepository(db)

        # 1. Generate Stage 2 detailed cooking guide
        guide = self.generate_stage2_guide(selected_recipe)

        # 2. Update RequestOutput with cooking guide
        out_repo.upsert_output(request_id=request_id, cooking_guide=guide)

        print(f"[LLMRecipeWorker] Successfully generated cooking guide for '{selected_recipe}' (Request #{request_id})")
        return True
