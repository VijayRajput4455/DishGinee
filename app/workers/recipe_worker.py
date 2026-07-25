import json
import urllib.request
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logger import get_logger
from app.enums import RequestStatus
from app.repositories import RequestOutputRepository, RequestRepository

logger = get_logger(__name__)


class LLMRecipeWorker:
    """Worker handling Stage 1 (5 candidate recipe options) and Stage 2 (full cooking guide) via Ollama / LLM."""

    def __init__(self) -> None:
        self.ollama_url = f"{settings.OLLAMA_BASE_URL}/api/generate"
        self.ollama_model = settings.OLLAMA_MODEL

    def _call_ollama(self, prompt: str) -> str | None:
        """Helper to invoke local Ollama LLM endpoint over HTTP POST."""
        payload = {
            "model": self.ollama_model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.ollama_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                if response.status == 200:
                    resp_body = json.loads(response.read().decode("utf-8"))
                    return resp_body.get("response")
        except Exception as e:
            logger.warning("Ollama service call to %s failed (%s). Using local fallback.", self.ollama_url, e)
        return None

    def generate_stage1_options(self, ingredients: list[str], cuisine: str | None = None) -> list[dict[str, Any]]:
        """Stage 1: Generate 5 distinct recipe options using Ollama local LLM."""
        ing_list_str = ", ".join(ingredients) if isinstance(ingredients, list) else str(ingredients)
        cuisine_str = f" {cuisine}" if cuisine else ""

        prompt = f"""
You are an expert chef. Given the available ingredients: [{ing_list_str}] and target cuisine preference:{cuisine_str if cuisine_str else ' Any'}, generate EXACTLY 5 distinct, delicious recipe options.

Return a JSON array containing 5 recipe objects with the following schema:
[
  {{
    "title": "Recipe Name",
    "description": "Short appetizing description",
    "prep_time": "15-20 mins",
    "matched_ingredients": ["list of ingredients used from input"],
    "missing_ingredients": ["extra staple ingredients required"]
  }}
]
Do not include any extra commentary. Output pure valid JSON.
"""

        raw_response = self._call_ollama(prompt)
        if raw_response:
            try:
                parsed = json.loads(raw_response)
                if isinstance(parsed, list) and len(parsed) >= 1:
                    logger.info("Successfully generated %s recipes via Ollama (%s).", len(parsed), self.ollama_model)
                    return parsed[:5]
                elif isinstance(parsed, dict) and "recipes" in parsed:
                    return parsed["recipes"][:5]
            except Exception as parse_err:
                logger.warning("Could not parse Ollama JSON response: %s", parse_err)

        # Fallback generator: Return 5 customized recipe options
        c_prefix = f"{cuisine.title()} " if cuisine else ""
        main_ing = ingredients[0].title() if ingredients else "Delight"
        sec_ing = ingredients[1].title() if len(ingredients) > 1 else "Special"
        third_ing = ingredients[2].title() if len(ingredients) > 2 else "Feast"

        return [
            {
                "title": f"{c_prefix}Garlic Butter {main_ing} & {sec_ing}",
                "description": f"A rich, comforting dish combining sautéed {main_ing.lower()} and {sec_ing.lower()} in melted butter.",
                "prep_time": "15 mins",
                "matched_ingredients": ingredients,
                "missing_ingredients": ["garlic", "black pepper", "herbs"],
            },
            {
                "title": f"Rustic {c_prefix}{main_ing} {third_ing} Curry / Stew",
                "description": f"Traditional hearty dish simmering {main_ing.lower()} with aromatic spices and herbs.",
                "prep_time": "20 mins",
                "matched_ingredients": ingredients,
                "missing_ingredients": ["onion", "cumin", "salt"],
            },
            {
                "title": f"{c_prefix}Pan-Seared {main_ing} with Golden {third_ing}",
                "description": f"Sizzling skillet meal pan-seared to perfection.",
                "prep_time": "25 mins",
                "matched_ingredients": ingredients,
                "missing_ingredients": ["olive oil", "lemon juice"],
            },
            {
                "title": f"Creamy {c_prefix}{sec_ing} & {main_ing} Bake",
                "description": f"Oven-baked casserole layering tender {sec_ing.lower()} and rich flavors.",
                "prep_time": "30 mins",
                "matched_ingredients": ingredients,
                "missing_ingredients": ["cream", "cheese"],
            },
            {
                "title": f"{c_prefix}Crispy Roasted {main_ing} Bowl",
                "description": f"Healthy bowl featuring roasted {main_ing.lower()} served with light herbs.",
                "prep_time": "15 mins",
                "matched_ingredients": ingredients,
                "missing_ingredients": ["sea salt", "parsley"],
            },
        ]

    def generate_stage2_guide(self, recipe_title: str) -> dict[str, Any]:
        """Stage 2: Generate detailed step-by-step cooking guide using Ollama / structured fallback."""
        prompt = f"""
You are a master chef. Generate a complete step-by-step cooking guide for the recipe titled '{recipe_title}'.
Return a valid JSON object matching this schema:
{{
  "title": "{recipe_title}",
  "servings": 2,
  "prep_time": "15 mins",
  "cook_time": "20 mins",
  "ingredients": ["list of ingredients with exact measurements"],
  "steps": [
    {{
      "step_number": 1,
      "instruction": "Detailed step instruction",
      "duration_minutes": 5,
      "equipment": ["Tools needed"]
    }}
  ],
  "macros": {{
    "calories": 450,
    "protein_g": 25.0,
    "carbs_g": 30.0,
    "fats_g": 18.0
  }},
  "substitutions": ["Ingredient substitution suggestions"]
}}
Output pure valid JSON only.
"""
        raw_response = self._call_ollama(prompt)
        if raw_response:
            try:
                parsed = json.loads(raw_response)
                if isinstance(parsed, dict) and "title" in parsed and "steps" in parsed:
                    logger.info("Successfully generated Stage 2 cooking guide via Ollama.")
                    return parsed
            except Exception as parse_err:
                logger.warning("Could not parse Stage 2 Ollama JSON: %s", parse_err)

        # Fallback Stage 2 guide
        return {
            "title": recipe_title,
            "servings": 2,
            "prep_time": "15 mins",
            "cook_time": "20 mins",
            "ingredients": [
                "250g Main Ingredient (Tomato / Potato / Protein)",
                "2 tbsp Butter / Olive Oil",
                "2 cloves Garlic, minced",
                "Salt and freshly ground black pepper to taste",
            ],
            "steps": [
                {
                    "step_number": 1,
                    "instruction": "Prep ingredients: Wash, peel, and cut tomatoes/potatoes into even bite-sized pieces.",
                    "duration_minutes": 5,
                    "equipment": ["Cutting board", "Chef knife"],
                },
                {
                    "step_number": 2,
                    "instruction": "Heat skillet: Melt butter over medium heat. Sauté garlic until aromatic (approx 1 min).",
                    "duration_minutes": 3,
                    "equipment": ["Non-stick Skillet", "Spatula"],
                },
                {
                    "step_number": 3,
                    "instruction": "Cook main ingredients: Add potatoes/tomatoes, cover and simmer on medium-low for 12-15 minutes until tender.",
                    "duration_minutes": 12,
                    "equipment": ["Skillet with lid"],
                },
                {
                    "step_number": 4,
                    "instruction": "Garnish & Serve: Season with salt, pepper, and fresh herbs. Serve hot.",
                    "duration_minutes": 2,
                    "equipment": ["Serving plate"],
                },
            ],
            "macros": {
                "calories": 420,
                "protein_g": 18.5,
                "carbs_g": 38.0,
                "fats_g": 20.0,
            },
            "substitutions": [
                "Use olive oil or Ghee in place of butter for high-heat roasting.",
            ],
        }

    def process_recipe_task(self, payload: dict[str, Any], db: Session) -> bool:
        """Process a Stage 1 candidate 5-recipe generation task."""
        request_id = payload.get("request_id")
        ingredients = payload.get("ingredients", [])
        cuisine = payload.get("cuisine")

        # Parse ingredients if passed as string or raw text fallback
        if isinstance(ingredients, str):
            ingredients = [item.strip() for item in ingredients.split(",") if item.strip()]
        elif not ingredients:
            raw_text = payload.get("raw_text_input") or payload.get("text")
            if raw_text and isinstance(raw_text, str):
                ingredients = [item.strip() for item in raw_text.split(",") if item.strip()]

        if not request_id:
            logger.error("Invalid payload missing request_id: %s", payload)
            return False

        req_repo = RequestRepository(db)
        out_repo = RequestOutputRepository(db)

        # 1. Generate 5 Stage 1 candidate recipe options using Ollama
        options = self.generate_stage1_options(ingredients, cuisine=cuisine)

        # 2. Update RequestOutput with candidate options payload
        out_repo.upsert_output(request_id=request_id, ingredients=options)

        # 3. Update Request status to COMPLETED
        req_repo.update_status(request_id=request_id, status=RequestStatus.COMPLETED)

        logger.info("Successfully generated %s recipes for Request #%s (Cuisine: %s)", len(options), request_id, cuisine or 'Any')
        return True

    def process_guide_task(self, payload: dict[str, Any], db: Session) -> bool:
        """Process a Stage 2 full cooking guide generation task."""
        request_id = payload.get("request_id")
        selected_recipe = payload.get("selected_recipe")

        if not request_id or not selected_recipe:
            logger.error("Invalid payload missing request_id or selected_recipe: %s", payload)
            return False

        out_repo = RequestOutputRepository(db)

        # 1. Generate Stage 2 detailed cooking guide
        guide = self.generate_stage2_guide(selected_recipe)

        # 2. Update RequestOutput with cooking guide
        out_repo.upsert_output(request_id=request_id, cooking_guide=guide)

        logger.info("Successfully generated cooking guide for '%s' (Request #%s)", selected_recipe, request_id)
        return True
