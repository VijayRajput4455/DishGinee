import json
import requests
import re
from app.logger import get_logger  # ✅ centralized logger

logger = get_logger(__name__)

# --- Configuration ---
OLLAMA_ENDPOINT = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2:latest"

class RecipeDetailGenerator:
    def __init__(self, model_name="llama3.2:latest"):
        self.model = model_name
        logger.info(f"Initialized RecipeDetailGenerator with model: {self.model}")

    def get_full_recipe(self, recipe_name):
        """
        Given a recipe name, return ingredients & cooking steps.
        """
        logger.info(f"Generating recipe details for: {recipe_name}")

        prompt = f"""
        You are a world-class chef and nutritionist.
        Provide the complete recipe for: "{recipe_name}".

        The response must be in **valid JSON** only, with no extra text.
        Include the following keys:

        {{
            "Recipe_Name": "...",
            "Description": "...",
            "Preparation_time": "...",
            "Cooking_time": "...",
            "Servings": "...",
            "Ingredients": ["...", "..."],
            "Instructions": [
                "Step 1: ...",
                "Step 2: ...",
                "Step 3: ... (include detailed cooking methods, timings, tips)",
                "... (continue until dish is ready)"
            ],
            "Nutrition": {{
                "Calories": "...",
                "Protein": "...",
                "Carbohydrates": "...",
                "Fat": "...",
                "Fiber": "...",
                "Other": "..."
            }},
            "Suggested_Ingredients": ["...", "..."]
        }}

        Rules:
        - Instructions must be very clear, step-by-step, and beginner-friendly.
        - Each instruction should explain **what to do, how to do it, and why if relevant**.
        - Nutrition values must be approximate per serving.
        - Suggested_Ingredients should list items that can make the dish healthier, tastier, or more authentic.
        - Return ONLY raw JSON (no markdown, no explanations).
        """

        try:
            response = requests.post(
                OLLAMA_ENDPOINT,
                json={"model": self.model, "prompt": prompt, "stream": True},
                timeout=120,
                stream=True
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to reach Ollama API: {e}")
            return {}

        # Collect the streamed output
        full_response = ""
        for line in response.iter_lines():
            if line:
                try:
                    data = json.loads(line.decode("utf-8"))
                    full_response += data.get("response", "")
                except json.JSONDecodeError:
                    logger.warning("Skipped a line due to JSONDecodeError")
                    continue

        # Extract JSON
        try:
            match = re.search(r"\{.*\}", full_response, re.DOTALL)
            if match:
                json_str = match.group(0)
                recipe_details = json.loads(json_str)
                logger.info(f"Successfully generated recipe details for: {recipe_name}")
            else:
                logger.warning(f"No JSON found in response for: {recipe_name}")
                recipe_details = {}
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON response for: {recipe_name}")
            logger.debug(f"Raw response: {full_response}")
            recipe_details = {}

        return recipe_details



# if __name__ == "__main__":
#     # Simulating user selection
#     selected_recipe = "Paneer Butter Masala"

#     generator = RecipeDetailGenerator()
#     recipe = generator.get_full_recipe(selected_recipe)

#     print("\n🍽 Full Recipe:")
#     print(json.dumps(recipe, indent=2))
