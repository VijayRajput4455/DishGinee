import json
import urllib.request
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logger import get_logger
from app.enums import RequestStatus
from app.repositories import RequestOutputRepository, RequestRepository

logger = get_logger(__name__)


class CookingGuideWorker:
    """Dedicated Stage 2 Worker: Takes selected recipe title and generates a complete cooking guide via Ollama LLM."""

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
            logger.warning("Ollama call to %s failed (%s). Using fallback guide.", self.ollama_url, e)
        return None

    def generate_full_cooking_guide(self, recipe_title: str) -> dict[str, Any]:
        """Generate full cooking guide with ingredients, steps, timings, equipment, and macros."""
        prompt = f"""
You are a master chef. Generate a complete, detailed cooking recipe guide for the dish: '{recipe_title}'.

Return a valid JSON object matching EXACTLY this schema:
{{
  "title": "{recipe_title}",
  "servings": 2,
  "prep_time": "15 mins",
  "cook_time": "20 mins",
  "ingredients": [
    "2 large Tomatoes, chopped",
    "2 medium Potatoes, boiled & diced",
    "2 tbsp Butter",
    "3 cloves Garlic, minced",
    "1/2 tsp Cumin seeds",
    "Salt & Red Chili Powder to taste"
  ],
  "steps": [
    {{
      "step_number": 1,
      "instruction": "Wash and chop tomatoes; boil, peel, and dice potatoes.",
      "duration_minutes": 5,
      "equipment": ["Cutting board", "Chef knife"]
    }},
    {{
      "step_number": 2,
      "instruction": "Melt butter in a pan over medium heat. Add cumin seeds and minced garlic; sauté until golden.",
      "duration_minutes": 3,
      "equipment": ["Frying pan / Skillet", "Spatula"]
    }},
    {{
      "step_number": 3,
      "instruction": "Add chopped tomatoes, salt, and spices. Cook until tomatoes turn soft and butter separates.",
      "duration_minutes": 7,
      "equipment": ["Skillet"]
    }},
    {{
      "step_number": 4,
      "instruction": "Add diced potatoes and toss gently to coat with tomato garlic butter sauce. Simmer for 5 mins.",
      "duration_minutes": 5,
      "equipment": ["Skillet"]
    }}
  ],
  "macros": {{
    "calories": 380,
    "protein_g": 8.5,
    "carbs_g": 42.0,
    "fats_g": 18.0
  }},
  "substitutions": [
    "Use Ghee or Olive Oil instead of butter for high heat frying.",
    "Substitute sweet potatoes for lower glycemic index."
  ]
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

    def process_cooking_guide_task(self, payload: dict[str, Any], db: Session) -> bool:
        """Consume RabbitMQ task, generate full cooking guide for selected recipe, and update DB."""
        request_id = payload.get("request_id")
        selected_recipe = payload.get("selected_recipe")

        if not request_id or not selected_recipe:
            logger.error("Invalid payload missing request_id or selected_recipe: %s", payload)
            return False

        out_repo = RequestOutputRepository(db)
        req_repo = RequestRepository(db)

        # 1. Generate full cooking guide using Ollama
        guide = self.generate_full_cooking_guide(selected_recipe)

        # 2. Store cooking guide payload in RequestOutput
        out_repo.upsert_output(request_id=request_id, cooking_guide=guide)

        # 3. Mark Request status as COMPLETED
        req_repo.update_status(request_id=request_id, status=RequestStatus.COMPLETED)

        logger.info("Task Finished! Complete cooking guide stored for '%s' (Request #%s)", selected_recipe, request_id)
        return True
