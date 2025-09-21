from fastapi import APIRouter, Form, HTTPException
from src.recipe_names_generator import RecipeNameGenerator
from app.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)
generator = RecipeNameGenerator()

@router.post("/")
async def generate_recipe_names(
    ingredients: str = Form(...), 
    cuisine: str = Form("Indian"), 
    num_recipes: int = Form(5)
):
    ingredients_list = [i.strip() for i in ingredients.split(",")]
    logger.info(f"Received request for recipe names. Ingredients: {ingredients_list}, Cuisine: {cuisine}, Count: {num_recipes}")

    try:
        recipes = generator.get_recipe_names(ingredients_list, cuisine, num_recipes)
        if not recipes:
            logger.warning(f"No recipes generated for ingredients: {ingredients_list} and cuisine: {cuisine}")
            raise HTTPException(status_code=400, detail="Could not generate recipe names.")

        logger.info(f"Generated recipes: {recipes}")
        return {"recipe_names": recipes}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating recipe names: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate recipe names: {str(e)}")
