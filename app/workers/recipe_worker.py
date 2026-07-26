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
            with urllib.request.urlopen(req, timeout=60) as response:
                if response.status == 200:
                    resp_body = json.loads(response.read().decode("utf-8"))
                    return resp_body.get("response")
        except Exception as e:
            logger.warning("Ollama service call to %s failed (%s). Using local fallback.", self.ollama_url, e)
        return None

    def generate_stage1_options(
        self,
        ingredients: list[str],
        cuisine: str | None = None,
        is_vegetarian: bool | None = None,
    ) -> list[dict[str, Any]]:
        """Stage 1: Generate 5 distinct recipe options using Ollama local LLM with dietary constraints."""
        ing_list_str = ", ".join(ingredients) if isinstance(ingredients, list) else str(ingredients)
        cuisine_str = f" {cuisine}" if cuisine else ""

        diet_instruction = ""
        if is_vegetarian is True:
            diet_instruction = "\nDIETARY CONSTRAINT: STRICTLY VEGETARIAN ONLY! All 5 recipes MUST be 100% vegetarian. Do NOT include chicken, meat, beef, pork, mutton, fish, seafood, or eggs in any recipe!"
        elif is_vegetarian is False:
            diet_instruction = "\nDIETARY PREFERENCE: Non-Vegetarian allowed."

        prompt = f"""
You are an expert chef. The user input is: [{ing_list_str}] and target cuisine preference:{cuisine_str if cuisine_str else ' Any'}.{diet_instruction}

Note: The user input may contain a list of raw ingredients OR a specific dish/recipe name (e.g. 'Paneer Butter Masala', 'Garlic Bread').
- If the input is a list of ingredients, generate 5 distinct recipes utilizing those ingredients.
- If the input is a specific recipe name, generate 5 delicious gourmet variations/styles of that dish (e.g. Classic, Restaurant-Style, Quick 15-Min, Smoky Tandoori, Creamy Garlic).

Return a JSON array containing EXACTLY 5 recipe objects with the following schema:
[
  {{
    "title": "Recipe Name",
    "description": "Short appetizing description",
    "prep_time": "15-20 mins",
    "matched_ingredients": ["list of key ingredients"],
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

        # Fallback generator: Return 5 customized recipe options based on dietary choice
        c_prefix = f"{cuisine.title()} " if cuisine else ""
        
        # Filter non-veg keywords if vegetarian requested
        non_veg_terms = {"chicken", "mutton", "beef", "pork", "fish", "prawn", "seafood", "egg", "meat"}
        clean_ings = ingredients
        if is_vegetarian:
            clean_ings = [i for i in ingredients if i.lower().strip() not in non_veg_terms]
            if not clean_ings:
                clean_ings = ["Paneer", "Tomatoes", "Garlic", "Butter"]

        main_ing = clean_ings[0].title() if clean_ings else "Vegetable"
        sec_ing = clean_ings[1].title() if len(clean_ings) > 1 else "Herbs"
        third_ing = clean_ings[2].title() if len(clean_ings) > 2 else "Spices"

        if is_vegetarian:
            return [
                {
                    "title": f"{c_prefix}Garlic Butter {main_ing} & {sec_ing}",
                    "description": f"A rich, comforting vegetarian dish combining sautéed {main_ing.lower()} and {sec_ing.lower()} in melted butter.",
                    "prep_time": "15 mins",
                    "matched_ingredients": clean_ings,
                    "missing_ingredients": ["garlic", "black pepper", "herbs"],
                },
                {
                    "title": f"Rustic {c_prefix}{main_ing} {third_ing} Curry / Stew",
                    "description": f"Traditional hearty vegetarian dish simmering {main_ing.lower()} with aromatic spices and herbs.",
                    "prep_time": "20 mins",
                    "matched_ingredients": clean_ings,
                    "missing_ingredients": ["onion", "cumin", "salt"],
                },
                {
                    "title": f"{c_prefix}Pan-Seared {main_ing} with Golden {third_ing}",
                    "description": f"Sizzling skillet vegetarian meal pan-seared to perfection.",
                    "prep_time": "25 mins",
                    "matched_ingredients": clean_ings,
                    "missing_ingredients": ["olive oil", "lemon juice"],
                },
                {
                    "title": f"Creamy {c_prefix}{sec_ing} & {main_ing} Bake",
                    "description": f"Oven-baked vegetarian casserole layering tender {sec_ing.lower()} and rich flavors.",
                    "prep_time": "30 mins",
                    "matched_ingredients": clean_ings,
                    "missing_ingredients": ["cream", "cheese"],
                },
                {
                    "title": f"{c_prefix}Crispy Roasted {main_ing} Bowl",
                    "description": f"Healthy vegetarian bowl featuring roasted {main_ing.lower()} served with light herbs.",
                    "prep_time": "15 mins",
                    "matched_ingredients": clean_ings,
                    "missing_ingredients": ["sea salt", "parsley"],
                },
            ]
        else:
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
    "calories": 380,
    "protein_g": 8.5,
    "carbs_g": 42.0,
    "fats_g": 18.0
  }},
  "substitutions": ["Ingredient substitution suggestions"]
}}
Do not include any intro or outro text. Return valid JSON only.
"""
        raw_response = self._call_ollama(prompt)
        if raw_response:
            try:
                parsed = json.loads(raw_response)
                if isinstance(parsed, dict) and "title" in parsed and "steps" in parsed:
                    logger.info("Successfully generated complete cooking guide via Ollama (%s) for '%s'.", self.ollama_model, recipe_title)
                    return parsed
            except Exception as parse_err:
                logger.warning("Could not parse JSON response from Ollama: %s", parse_err)

        # Fallback detailed cooking guide tailored to recipe_title
        words = [w.strip() for w in recipe_title.split() if len(w) > 3]
        dish_name = recipe_title.title()
        main_component = words[0] if words else "Ingredients"

        return {
            "title": dish_name,
            "servings": 2,
            "prep_time": "15 mins",
            "cook_time": "20 mins",
            "ingredients": [
                f"Fresh {main_component} (main ingredient)",
                "Aromatic spices & seasonings",
                "2 tbsp Cooking butter or oil",
                "Fresh garlic & herbs",
                "Salt & pepper to taste",
            ],
            "steps": [
                {
                    "step_number": 1,
                    "instruction": f"Prepare fresh ingredients for {dish_name}. Wash, chop, and mince all key components.",
                    "duration_minutes": 5,
                    "equipment": ["Cutting board", "Chef knife"],
                },
                {
                    "step_number": 2,
                    "instruction": "Heat skillet or cooking pot over medium flame with butter or oil. Sauté aromatics until fragrant.",
                    "duration_minutes": 4,
                    "equipment": ["Skillet / Pan", "Spatula"],
                },
                {
                    "step_number": 3,
                    "instruction": f"Combine {main_component.lower()} and seasonings. Cook gently, stirring occasionally to infuse rich flavors.",
                    "duration_minutes": 8,
                    "equipment": ["Skillet / Pan"],
                },
                {
                    "step_number": 4,
                    "instruction": f"Simmer {dish_name} until perfectly cooked and tender. Garnish with fresh herbs and serve warm.",
                    "duration_minutes": 3,
                    "equipment": ["Serving plate / Bowl"],
                },
            ],
            "macros": {
                "calories": 410,
                "protein_g": 14.5,
                "carbs_g": 45.0,
                "fats_g": 16.0,
            },
            "substitutions": [
                "Substitute butter with olive oil or ghee according to preference.",
                "Adjust chili powder or black pepper for desired heat level.",
            ],
        }

    def process_recipe_task(self, payload: dict[str, Any], db: Session) -> bool:
        """Process a Stage 1 candidate 5-recipe generation task."""
        request_id = payload.get("request_id")
        ingredients = payload.get("ingredients", [])
        cuisine = payload.get("cuisine")
        is_vegetarian = payload.get("is_vegetarian")

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
        options = self.generate_stage1_options(ingredients, cuisine=cuisine, is_vegetarian=is_vegetarian)

        # 2. Update RequestOutput with candidate options payload
        out_repo.upsert_output(request_id=request_id, ingredients=options)

        # 3. Update Request status to COMPLETED
        req_repo.update_status(request_id=request_id, status=RequestStatus.COMPLETED)

        logger.info("Successfully generated %s recipes for Request #%s (Cuisine: %s, Veg: %s)", len(options), request_id, cuisine or 'Any', is_vegetarian)
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
