import json
import re
import requests
from app.logger import get_logger  # ✅ centralized logger

logger = get_logger(__name__)

# --- Configuration ---
OLLAMA_ENDPOINT = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2:latest"

class RecipeNameGenerator:
    def __init__(self, model_name="llama3.2:latest"):
        self.model = model_name
        logger.info(f"Initialized RecipeNameGenerator with model: {self.model}")

    def get_recipe_names(self, ingredients, cuisine, num_recipes=5):
        """
        Given a list of ingredients and desired cuisine, return recipe names.
        """
        logger.info(f"Generating {num_recipes} recipe names for cuisine '{cuisine}' with ingredients: {ingredients}")
        ingredients_str = ", ".join(ingredients)

        prompt = f"""
        You are a professional chef.
        I have the following ingredients: {ingredients_str}.
        I want {num_recipes} creative recipe names from {cuisine} cuisine only.

        Return ONLY raw JSON in the following format:
        [
          "Recipe Name 1",
          "Recipe Name 2",
          "Recipe Name 3"
        ]

        IMPORTANT: No markdown, no explanation, no extra text.
        """

        try:
            response = requests.post(
                OLLAMA_ENDPOINT,
                json={"model": self.model, "prompt": prompt, "stream": True},
                timeout=120,
                stream=True
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"Request to Ollama API failed: {e}")
            return []

        # Collect streamed output
        full_response = ""
        for line in response.iter_lines():
            if line:
                try:
                    data = json.loads(line.decode("utf-8"))
                    full_response += data.get("response", "")
                except json.JSONDecodeError:
                    logger.warning("Skipped a line due to JSONDecodeError in streamed response")
                    continue

        # Extract JSON array
        try:
            match = re.search(r"\[.*?\]", full_response, re.DOTALL)
            if match:
                json_str = match.group(0)
                try:
                    recipes = json.loads(json_str)
                    logger.info(f"Generated recipes successfully: {recipes}")
                except json.JSONDecodeError:
                    # Fix trailing commas
                    json_str = re.sub(r",\s*]", "]", json_str)
                    recipes = json.loads(json_str)
                    logger.info(f"Generated recipes successfully after fixing JSON: {recipes}")
            else:
                logger.warning("No JSON array found in response")
                recipes = []
        except json.JSONDecodeError:
            logger.error("Could not parse JSON from response")
            logger.debug(f"Raw response: {full_response}")
            recipes = []

        return recipes



# if __name__ == "__main__":
#     ingredients_list = ["tomato", "onion", "garlic"]
#     desired_cuisine = "Indian"  # user can input: "French", "Italian", "Mexican", etc.

#     generator = RecipeNameGenerator()
#     recipes = generator.get_recipe_names(ingredients_list, desired_cuisine, num_recipes=5)

#     print(f"\n🍽 Suggested {desired_cuisine} Recipes:")
#     for i, recipe in enumerate(recipes, start=1):
#         print(f"{i}. {recipe}")
