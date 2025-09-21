from fastapi import FastAPI
from app.endpoints import detect, recipes_details, recipes_names
from app.logger import get_logger

# Initialize logger
logger = get_logger(__name__)


# Create FastAPI app
app = FastAPI(
    title="DishGeniee API",
    description="Food detection, recipe name generation, and full recipe details API",
    version="1.0.0"
)

# YOLO Detection Endpoint
app.include_router(detect.router, prefix="/detection", tags=["Detection"])

# Recipe Name Generator Endpoint
app.include_router(recipes_names.router, prefix="/recipes_names", tags=["Recipes Names"])

# Recipe Detail Generator Endpoint
app.include_router(recipes_details.router, prefix="/recipes_details", tags=["Recipe Details"])


logger.info("FastAPI application initialized with all endpoints")


# Optional: Root endpoint
@app.get("/")
async def root():
    logger.info("Root endpoint accessed")
    return {"message": "Welcome to DishGeniee API! Use /docs for interactive API docs."}
