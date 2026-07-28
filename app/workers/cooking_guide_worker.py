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
You are an executive master chef and expert nutritionist. Generate a complete, authentic, step-by-step cooking recipe guide specifically for the dish: '{recipe_title}'.

Generate exact ingredients with measurements, step-by-step preparation instructions with duration in minutes, equipment needed, and calculate authentic, dish-specific nutritional macros for '{recipe_title}'.

Return a valid JSON object matching this schema:
{{
  "title": "{recipe_title}",
  "servings": 2,
  "prep_time_minutes": 15,
  "cook_time_minutes": 20,
  "ingredients": [
    "1st required ingredient with exact quantity",
    "2nd required ingredient with exact quantity",
    "3rd required ingredient with exact quantity",
    "4th required ingredient with exact quantity"
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
    "calories": "Calculated total calories for {recipe_title}",
    "protein_g": "Calculated protein in grams for {recipe_title}",
    "carbs_g": "Calculated carbs in grams for {recipe_title}",
    "fats_g": "Calculated fats in grams for {recipe_title}"
  }},
  "substitutions": [
    "Chef pro tip or substitution suggestion for {recipe_title}"
  ]
}}
CRITICAL RULE: Calculate real, authentic nutritional macros using your LLM model for '{recipe_title}'. Make sure "duration_minutes" is a valid integer for each step. Return valid JSON only.
"""

        raw_response = self._call_ollama(prompt)
        if raw_response:
            try:
                cleaned = raw_response.strip()
                if cleaned.startswith("```json"):
                    cleaned = cleaned[7:]
                if cleaned.startswith("```"):
                    cleaned = cleaned[3:]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
                cleaned = cleaned.strip()

                parsed = json.loads(cleaned)
                if isinstance(parsed, dict):
                    # Ensure title is present
                    if "title" not in parsed:
                        parsed["title"] = recipe_title

                    # Normalize macros directly from LLM output
                    if "macros" not in parsed and "nutritional_information" in parsed:
                        parsed["macros"] = parsed["nutritional_information"]
                    if "macros" in parsed and isinstance(parsed["macros"], dict):
                        m = parsed["macros"]
                        if "calories" not in m: m["calories"] = m.get("cals", 350)
                        if "protein_g" not in m: m["protein_g"] = m.get("protein", 15)
                        if "carbs_g" not in m: m["carbs_g"] = m.get("carbs", 40)
                        if "fats_g" not in m: m["fats_g"] = m.get("fats", 12)
                    else:
                        parsed["macros"] = {"calories": 380, "protein_g": 15, "carbs_g": 40, "fats_g": 12}

                    # Normalize ingredients list (converting dict items if LLM returned dicts)
                    if "ingredients" not in parsed or not isinstance(parsed["ingredients"], list) or not parsed["ingredients"]:
                        parsed["ingredients"] = [f"Fresh main ingredients for {recipe_title}", "2 tbsp Butter or Olive oil", "Fresh garlic & herbs", "Salt & seasonings to taste"]
                    else:
                        clean_ings = []
                        for item in parsed["ingredients"]:
                            if isinstance(item, str):
                                clean_ings.append(item)
                            elif isinstance(item, dict):
                                name = item.get("name") or item.get("item") or item.get("ingredient") or "Ingredient"
                                amount = item.get("amount") or item.get("quantity") or ""
                                clean_ings.append(f"{amount} {name}".strip())
                        parsed["ingredients"] = clean_ings

                    # Normalize steps (guaranteeing duration_minutes is present)
                    if "steps" in parsed and isinstance(parsed["steps"], list) and len(parsed["steps"]) >= 1:
                        clean_steps = []
                        for idx, st in enumerate(parsed["steps"]):
                            if isinstance(st, str):
                                clean_steps.append({
                                    "step_number": idx + 1,
                                    "instruction": st,
                                    "duration_minutes": 5,
                                    "equipment": ["Kitchen Tools"]
                                })
                            elif isinstance(st, dict):
                                dur = st.get("duration_minutes") or st.get("duration") or st.get("time_minutes") or st.get("time") or 5
                                try: dur = int(dur)
                                except Exception: dur = 5
                                st["duration_minutes"] = dur
                                st["step_number"] = st.get("step_number") or st.get("step") or idx + 1
                                st["instruction"] = st.get("instruction") or st.get("description") or st.get("text") or "Follow recipe preparation step."
                                clean_steps.append(st)
                        parsed["steps"] = clean_steps
                        logger.info("Successfully generated complete cooking guide via Ollama (%s) for '%s'.", self.ollama_model, recipe_title)
                        return parsed
            except Exception as parse_err:
                logger.warning("Could not parse JSON response from Ollama: %s", parse_err)

        logger.error("Ollama LLM model failed to return valid cooking guide JSON for '%s'.", recipe_title)
        return {}

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

