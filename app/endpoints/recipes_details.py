from fastapi import APIRouter, Form, HTTPException
from src.recipe_details_generator import RecipeDetailGenerator
from app.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)
generator = RecipeDetailGenerator()

@router.post("/")
async def get_recipe_details(recipe_name: str = Form(...)):
    """
    Provide a recipe name and get full recipe details.
    """
    logger.info(f"Received request for recipe details: {recipe_name}")
    
    if not recipe_name.strip():
        logger.warning("Empty recipe name provided")
        raise HTTPException(status_code=400, detail="Recipe name must not be empty.")

    try:
        details = generator.get_full_recipe(recipe_name)
        if not details:
            logger.warning(f"Recipe details not found for: {recipe_name}")
            raise HTTPException(status_code=404, detail=f"Could not generate recipe details for '{recipe_name}'.")

        logger.info(f"Generated recipe details for: {recipe_name}")
        return details

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating recipe details for '{recipe_name}': {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate recipe details: {str(e)}")
