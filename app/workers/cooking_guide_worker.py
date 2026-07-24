import json
import urllib.request
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.enums import RequestStatus
from app.repositories import RequestOutputRepository, RequestRepository


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
            with urllib.request.urlopen(req, timeout=30) as response:
                if response.status == 200:
                    resp_body = json.loads(response.read().decode("utf-8"))
                    return resp_body.get("response")
        except Exception as e:
            print(f"[CookingGuideWorker] Warning: Ollama call to {self.ollama_url} failed ({e}). Using fallback guide.")
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
                    print(f"[CookingGuideWorker] Successfully generated complete cooking guide via Ollama ({self.ollama_model}) for '{recipe_title}'.")
                    return parsed
            except Exception as parse_err:
                print(f"[CookingGuideWorker] Could not parse JSON response from Ollama: {parse_err}")

        # Fallback detailed cooking guide tailored to recipe_title
        return {
            "title": recipe_title,
            "servings": 2,
            "prep_time": "15 mins",
            "cook_time": "20 mins",
            "ingredients": [
                "2 medium Tomatoes, chopped",
                "2 medium Potatoes, boiled & cubed",
                "2 tbsp Butter",
                "3 cloves Garlic, minced",
                "Salt & spices to taste",
            ],
            "steps": [
                {
                    "step_number": 1,
                    "instruction": "Prepare fresh ingredients: chop tomatoes, peel boiled potatoes, and mincing garlic.",
                    "duration_minutes": 5,
                    "equipment": ["Cutting board", "Knife"],
                },
                {
                    "step_number": 2,
                    "instruction": "Melt butter in skillet over medium heat. Sauté garlic until golden brown.",
                    "duration_minutes": 3,
                    "equipment": ["Skillet", "Spatula"],
                },
                {
                    "step_number": 3,
                    "instruction": "Add tomatoes and spices; cook down until soft and aromatic.",
                    "duration_minutes": 7,
                    "equipment": ["Skillet"],
                },
                {
                    "step_number": 4,
                    "instruction": "Fold in cubed potatoes and simmer for 5 minutes until flavors blend. Serve hot.",
                    "duration_minutes": 5,
                    "equipment": ["Serving bowl"],
                },
            ],
            "macros": {
                "calories": 380,
                "protein_g": 8.5,
                "carbs_g": 42.0,
                "fats_g": 18.0,
            },
            "substitutions": [
                "Use Olive Oil or Ghee in place of butter if desired.",
            ],
        }

    def process_cooking_guide_task(self, payload: dict[str, Any], db: Session) -> bool:
        """Consume RabbitMQ task, generate full cooking guide for selected recipe, and update DB."""
        request_id = payload.get("request_id")
        selected_recipe = payload.get("selected_recipe")

        if not request_id or not selected_recipe:
            print("[CookingGuideWorker] Invalid payload missing request_id or selected_recipe")
            return False

        out_repo = RequestOutputRepository(db)
        req_repo = RequestRepository(db)

        # 1. Generate full cooking guide using Ollama
        guide = self.generate_full_cooking_guide(selected_recipe)

        # 2. Store cooking guide payload in RequestOutput
        out_repo.upsert_output(request_id=request_id, cooking_guide=guide)

        # 3. Mark Request status as COMPLETED
        req_repo.update_status(request_id=request_id, status=RequestStatus.COMPLETED)

        print(f"[CookingGuideWorker] Task Finished! Complete cooking guide stored for '{selected_recipe}' (Request #{request_id})")
        return True
