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
        """Generate full cooking guide with authentic ingredients, steps, timings, equipment, and macros for recipe_title."""
        prompt = f"""
You are a master chef. Generate a complete, authentic, step-by-step cooking recipe guide specifically for the dish: '{recipe_title}'.

Generate exact ingredients with quantities, step-by-step preparation instructions, cooking times, equipment needed, and nutritional macros tailored ONLY to '{recipe_title}'. Do NOT output generic tomato/potato steps unless '{recipe_title}' actually calls for them.

Return a valid JSON object matching this schema:
{{
  "title": "{recipe_title}",
  "servings": 2,
  "prep_time": "15 mins",
  "cook_time": "20 mins",
  "ingredients": [
    "1st required ingredient with quantity for {recipe_title}",
    "2nd required ingredient with quantity for {recipe_title}",
    "3rd required ingredient with quantity for {recipe_title}",
    "4th required ingredient with quantity for {recipe_title}"
  ],
  "steps": [
    {{
      "step_number": 1,
      "instruction": "Specific step 1 prep instruction for {recipe_title}.",
      "duration_minutes": 5,
      "equipment": ["Tool 1", "Tool 2"]
    }},
    {{
      "step_number": 2,
      "instruction": "Specific step 2 cooking instruction for {recipe_title}.",
      "duration_minutes": 10,
      "equipment": ["Pan / Pot"]
    }},
    {{
      "step_number": 3,
      "instruction": "Specific step 3 finishing instruction for {recipe_title}.",
      "duration_minutes": 5,
      "equipment": ["Plate"]
    }}
  ],
  "macros": {{
    "calories": 420,
    "protein_g": 14.0,
    "carbs_g": 48.0,
    "fats_g": 16.0
  }},
  "substitutions": [
    "Chef pro tip or substitution suggestion for {recipe_title}"
  ]
}}
Do not include any intro or outro text. Return valid JSON only.
"""

        raw_response = self._call_ollama(prompt)
        if raw_response:
            try:
                parsed = json.loads(raw_response)
                if isinstance(parsed, dict) and "title" in parsed and "steps" in parsed and len(parsed["steps"]) >= 1:
                    logger.info("Successfully generated complete cooking guide via Ollama (%s) for '%s'.", self.ollama_model, recipe_title)
                    return parsed
            except Exception as parse_err:
                logger.warning("Could not parse JSON response from Ollama: %s", parse_err)

        # Smart dynamic fallback tailored specifically to recipe_title
        title_lower = recipe_title.lower()
        
        if "garlic bread" in title_lower:
            return {
                "title": recipe_title.title(),
                "servings": 2,
                "prep_time": "10 mins",
                "cook_time": "12 mins",
                "ingredients": [
                    "1 French baguette or Italian loaf, halved",
                    "4 tbsp salted butter, softened",
                    "4 cloves garlic, finely minced",
                    "1 tbsp fresh parsley, chopped",
                    "1/2 cup mozzarella cheese, grated (optional)",
                    "1/2 tsp dried oregano or Italian seasoning"
                ],
                "steps": [
                    {
                        "step_number": 1,
                        "instruction": "Preheat oven to 375°F (190°C). Slice bread horizontally into two long halves.",
                        "duration_minutes": 3,
                        "equipment": ["Oven", "Bread Knife", "Baking Sheet"]
                    },
                    {
                        "step_number": 2,
                        "instruction": "In a bowl, mix softened butter, minced garlic, chopped parsley, and oregano into a spreadable garlic butter paste.",
                        "duration_minutes": 4,
                        "equipment": ["Mixing Bowl", "Butter Spreader / Knife"]
                    },
                    {
                        "step_number": 3,
                        "instruction": "Generously spread garlic butter over cut sides of bread. Top with grated mozzarella cheese if desired.",
                        "duration_minutes": 2,
                        "equipment": ["Baking Sheet"]
                    },
                    {
                        "step_number": 4,
                        "instruction": "Bake in oven for 10-12 minutes until bread is crispy and cheese is melted golden brown. Slice and serve warm.",
                        "duration_minutes": 10,
                        "equipment": ["Oven", "Cutting Board"]
                    }
                ],
                "macros": { "calories": 340, "protein_g": 9.0, "carbs_g": 38.0, "fats_g": 16.0 },
                "substitutions": [
                    "Use olive oil instead of butter for a dairy-free option.",
                    "Add chili flakes for extra spicy garlic bread."
                ]
            }
        
        if "paneer" in title_lower or "butter masala" in title_lower:
            return {
                "title": recipe_title.title(),
                "servings": 2,
                "prep_time": "15 mins",
                "cook_time": "20 mins",
                "ingredients": [
                    "250g Paneer (Cottage Cheese), cut into cubes",
                    "3 large ripe Tomatoes, pureed",
                    "2 tbsp Butter + 1 tbsp Oil",
                    "1 tbsp Ginger-Garlic paste",
                    "2 tbsp Heavy Cream or Cashew paste",
                    "1 tsp Garam Masala & Kasuri Methi",
                    "Salt & Red Chili Powder to taste"
                ],
                "steps": [
                    {
                        "step_number": 1,
                        "instruction": "Puree tomatoes, ginger, and garlic into a smooth puree. Cut paneer into 1-inch cubes.",
                        "duration_minutes": 5,
                        "equipment": ["Blender", "Knife", "Cutting Board"]
                    },
                    {
                        "step_number": 2,
                        "instruction": "Melt butter with oil in a pan. Add ginger-garlic paste and tomato puree; cook until oil separates.",
                        "duration_minutes": 7,
                        "equipment": ["Pan / Kadhai", "Spatula"]
                    },
                    {
                        "step_number": 3,
                        "instruction": "Add chili powder, garam masala, and salt. Stir in cream or cashew paste to form a rich velvety gravy.",
                        "duration_minutes": 3,
                        "equipment": ["Pan / Kadhai"]
                    },
                    {
                        "step_number": 4,
                        "instruction": "Add paneer cubes, simmer gently for 5 minutes, sprinkle crushed kasuri methi, and serve hot with naan.",
                        "duration_minutes": 5,
                        "equipment": ["Pan / Kadhai", "Serving Dish"]
                    }
                ],
                "macros": { "calories": 420, "protein_g": 16.0, "carbs_g": 18.0, "fats_g": 32.0 },
                "substitutions": [
                    "Substitute Paneer with Tofu for a vegan version.",
                    "Use soaked cashew paste instead of heavy cream for rich texture."
                ]
            }

        # Generic dynamic fallback for any other dish title
        words = [w.strip().title() for w in recipe_title.split() if len(w) > 2]
        dish_name = recipe_title.title()
        main_component = words[0] if words else "Main Ingredient"
        sec_component = words[1] if len(words) > 1 else "Seasoning"

        return {
            "title": dish_name,
            "servings": 2,
            "prep_time": "15 mins",
            "cook_time": "20 mins",
            "ingredients": [
                f"Fresh {main_component} (main ingredient for {dish_name})",
                f"Fresh {sec_component} & seasonings",
                "2 tbsp Butter or Olive oil",
                "Minced garlic & fresh herbs",
                "Salt & pepper to taste"
            ],
            "steps": [
                {
                    "step_number": 1,
                    "instruction": f"Prepare fresh ingredients for {dish_name}. Wash, slice, and measure out key components.",
                    "duration_minutes": 5,
                    "equipment": ["Cutting board", "Chef knife"]
                },
                {
                    "step_number": 2,
                    "instruction": f"Heat pan over medium flame with butter or oil. Sauté garlic and aromatics until fragrant.",
                    "duration_minutes": 4,
                    "equipment": ["Skillet / Pan", "Spatula"]
                },
                {
                    "step_number": 3,
                    "instruction": f"Add {main_component.lower()} and seasonings to pan. Cook gently over medium flame to infuse flavors.",
                    "duration_minutes": 8,
                    "equipment": ["Skillet / Pan"]
                },
                {
                    "step_number": 4,
                    "instruction": f"Simmer {dish_name} until cooked to perfection. Garnish with fresh herbs and serve warm.",
                    "duration_minutes": 3,
                    "equipment": ["Serving Dish"]
                }
            ],
            "macros": { "calories": 390, "protein_g": 14.0, "carbs_g": 40.0, "fats_g": 15.0 },
            "substitutions": [
                "Adjust chili powder or black pepper for desired heat level.",
                "Substitute butter with olive oil or ghee according to preference."
            ]
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

        # 1. DB CACHE LOOKUP or Direct LLM Generation
        force_llm = payload.get("force_llm", False)
        cached_guide = None if force_llm else req_repo.find_existing_cooking_guide(selected_recipe)
        
        if cached_guide:
            logger.info("⚡ CACHE HIT! Found existing cooking guide in DB for '%s'. Skipping Ollama LLM call!", selected_recipe)
            guide = cached_guide
        else:
            logger.info("🤖 Generating fresh Master Cooking Guide via Ollama LLM for '%s'...", selected_recipe)
            guide = self.generate_full_cooking_guide(selected_recipe)

        # 2. Store cooking guide payload in RequestOutput
        out_repo.upsert_output(request_id=request_id, cooking_guide=guide)

        # 3. Mark Request status as COMPLETED
        req_repo.update_status(request_id=request_id, status=RequestStatus.COMPLETED)

        logger.info("Task Finished! Complete cooking guide stored for '%s' (Request #%s)", selected_recipe, request_id)
        return True

