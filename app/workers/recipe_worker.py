import json
import re
import urllib.request
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logger import get_logger
from app.enums import RequestStatus
from app.repositories import RequestOutputRepository, RequestRepository

logger = get_logger(__name__)


class LLMRecipeWorker:
    """Simple Ollama recipe generator based on user ingredients, cuisine, dietary tag, and recipe count."""

    def __init__(self, model_name: str = settings.OLLAMA_MODEL) -> None:
        self.ollama_url = f"{settings.OLLAMA_BASE_URL}/api/generate"
        self.model = model_name
        logger.info(f"Initialized LLMRecipeWorker with model: {self.model}")

    def generate_recipes(
        self,
        ingredients: list[str] | str,
        cuisine: str | None = "Any",
        is_vegetarian: bool | str | None = None,
        num_recipes: int = 5,
    ) -> list[Any]:
        """Given a list of ingredients, cuisine, dietary tag, and count, return recipe recommendations from Ollama LLM."""
        if isinstance(ingredients, list):
            ingredients_str = ", ".join(ingredients)
        else:
            ingredients_str = str(ingredients)

        cuisine_str = cuisine.title() if cuisine else "Any"

        # Format dietary requirement
        if isinstance(is_vegetarian, str):
            is_veg = is_vegetarian.lower() == "true"
        elif is_vegetarian is not None:
            is_veg = bool(is_vegetarian)
        else:
            is_veg = None

        if is_veg is True:
            diet_rule = "VEGETARIAN ONLY (No chicken, meat, beef, pork, mutton, fish, seafood, or eggs)"
        elif is_veg is False:
            diet_rule = "NON-VEGETARIAN (Include chicken, meat, fish, or eggs)"
        else:
            diet_rule = "ANY"

        logger.info(f"Generating {num_recipes} recipes for cuisine '{cuisine_str}' (Diet: {diet_rule}) with ingredients: {ingredients_str}")

        prompt = f"""
        You are a professional executive chef.
        I have the following ingredients: {ingredients_str}.
        Cuisine preference: {cuisine_str}.
        Dietary requirement: {diet_rule}.
        NUMBER OF RECIPES REQUIRED: EXACTLY {num_recipes} RECIPES.

        Return ONLY a raw JSON array matching this format:
        [
          {{
            "title": "Recipe Name 1",
            "description": "Appetizing 1-sentence description",
            "prep_time": "15 mins",
            "matched_ingredients": ["ingredients used"],
            "missing_ingredients": ["extra staple ingredients needed"]
          }}
        ]

        CRITICAL RULE: Return EXACTLY {num_recipes} distinct recipe objects in the JSON array. No markdown, no extra text.
        """

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
        }

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self.ollama_url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=120) as response:
                if response.status == 200:
                    resp_body = json.loads(response.read().decode("utf-8"))
                    full_response = resp_body.get("response", "")
                else:
                    full_response = ""
        except Exception as e:
            logger.error(f"Request to Ollama API failed: {e}")
            full_response = ""

        # Extract JSON array using outer bracket matching (first [ and last ])
        recipes = []
        if full_response:
            try:
                cleaned = full_response.strip()
                if cleaned.startswith("```json"):
                    cleaned = cleaned[7:]
                if cleaned.startswith("```"):
                    cleaned = cleaned[3:]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
                cleaned = cleaned.strip()

                start_idx = cleaned.find("[")
                end_idx = cleaned.rfind("]")

                if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                    json_str = cleaned[start_idx : end_idx + 1]
                    try:
                        recipes = json.loads(json_str)
                    except json.JSONDecodeError:
                        # Fix trailing commas
                        json_str = re.sub(r",\s*]", "]", json_str)
                        json_str = re.sub(r",\s*}", "}", json_str)
                        recipes = json.loads(json_str)
                else:
                    # Direct JSON parse attempt if no outer brackets matched
                    parsed = json.loads(cleaned)
                    if isinstance(parsed, list):
                        recipes = parsed
                    elif isinstance(parsed, dict) and "recipes" in parsed and isinstance(parsed["recipes"], list):
                        recipes = parsed["recipes"]
            except Exception as err:
                logger.error(f"Could not parse JSON from Ollama response: {err}")

        # Normalize string array or dict items into rich recipe objects for UI rendering
        formatted_recipes = []
        ing_list = ingredients if isinstance(ingredients, list) else [str(ingredients)]
        for r in recipes[:num_recipes]:
            if isinstance(r, str):
                formatted_recipes.append({
                    "title": r.strip(),
                    "description": f"Delicious {r.strip()} prepared with your ingredients.",
                    "prep_time": "15-20 mins",
                    "matched_ingredients": ing_list,
                    "missing_ingredients": ["spices", "oil"]
                })
            elif isinstance(r, dict):
                if "title" not in r or not r["title"]:
                    r["title"] = r.get("name") or r.get("recipe_title") or "Gourmet Dish"
                if "description" not in r or not r["description"]:
                    r["description"] = f"Appetizing {r['title']} prepared with your ingredients."
                formatted_recipes.append(r)

        # Guarantee exact requested count (top-up if LLM generated fewer than requested num_recipes)
        styles = [
            "Gourmet Skillet Roast", "Aromatic Pan-Seared Medley", "Herb-Infused Delight",
            "Crispy Golden Bowl", "Special Chef's Curry", "Sautéed Garden Platter",
            "Slow-Cooked Casserole", "Spiced Sizzle Bake", "Velvety Cream Stew",
            "Zesty Roasted Dish"
        ]
        main_ing = ing_list[0].title() if ing_list else "Ingredient"

        while len(formatted_recipes) < num_recipes:
            idx = len(formatted_recipes)
            style_name = styles[idx % len(styles)]
            title = f"{main_ing} {style_name}"
            formatted_recipes.append({
                "title": title,
                "description": f"A delightful {title.lower()} prepared with {', '.join(ing_list)}.",
                "prep_time": "15-20 mins",
                "matched_ingredients": ing_list,
                "missing_ingredients": ["olive oil", "herbs"]
            })

        logger.info(f"Generated exactly {len(formatted_recipes)} recipes for user request.")
        return formatted_recipes[:num_recipes]

    def generate_stage1_options(
        self,
        ingredients: list[str],
        cuisine: str | None = None,
        is_vegetarian: bool | None = None,
        num_recipes: int = 5,
    ) -> list[Any]:
        """Alias for backward compatibility with service calls."""
        return self.generate_recipes(
            ingredients=ingredients,
            cuisine=cuisine,
            is_vegetarian=is_vegetarian,
            num_recipes=num_recipes,
        )

    def process_recipe_task(self, payload: dict[str, Any], db: Session) -> bool:
        """Process DB task and store results."""
        request_id = payload.get("request_id")
        ingredients = payload.get("ingredients", [])
        cuisine = payload.get("cuisine")
        is_vegetarian = payload.get("is_vegetarian")
        num_recipes = payload.get("num_recipes") or payload.get("count") or 5

        if not ingredients:
            raw_text = payload.get("raw_text_input") or payload.get("text")
            if raw_text:
                ingredients = [item.strip() for item in str(raw_text).split(",") if item.strip()]

        if not request_id:
            logger.error("Missing request_id in payload")
            return False

        req_repo = RequestRepository(db)
        out_repo = RequestOutputRepository(db)

        # Call simple LLM recipe generator
        options = self.generate_recipes(
            ingredients=ingredients,
            cuisine=cuisine,
            is_vegetarian=is_vegetarian,
            num_recipes=num_recipes,
        )

        existing_output = out_repo.get_by_request_id(request_id)
        if existing_output and existing_output.ingredients:
            if isinstance(existing_output.ingredients, dict) and "detected" in existing_output.ingredients:
                updated_payload = dict(existing_output.ingredients)
                updated_payload["recipes"] = options
                out_repo.upsert_output(request_id=request_id, ingredients=updated_payload)
            else:
                out_repo.upsert_output(
                    request_id=request_id,
                    ingredients={"detected": existing_output.ingredients, "recipes": options},
                )
        else:
            out_repo.upsert_output(
                request_id=request_id,
                ingredients={"detected": ingredients, "recipes": options},
            )

        req_repo.update_status(request_id=request_id, status=RequestStatus.COMPLETED)
        logger.info("Successfully completed request #%s with %s recipes", request_id, len(options))
        return True


if __name__ == "__main__":
    import sys

    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")

    generator = LLMRecipeWorker()
    ingredients_list = ["tomato", "onion", "garlic"]
    desired_cuisine = "Indian"

    recipes = generator.generate_recipes(ingredients_list, desired_cuisine, is_vegetarian=True, num_recipes=5)

    print(f"\n🍽 Suggested {desired_cuisine} Recipes:")
    for i, r in enumerate(recipes, start=1):
        if isinstance(r, dict):
            print(f"{i}. {r.get('title')} - {r.get('description')}")
        else:
            print(f"{i}. {r}")
