from fastapi import APIRouter, UploadFile, File, HTTPException
import shutil
import os
from typing import List
from src.food_detector import FoodDetector
from app.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)
detector = FoodDetector()

# Folder to save uploaded images
UPLOAD_DIR = "images"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/")
async def detect_ingredients(files: List[UploadFile] = File(...)):
    """
    Upload one or more images and detect ingredients using YOLO.
    Returns a list of detected ingredients and saved image paths.
    """
    if not files:
        logger.warning("No files uploaded")
        raise HTTPException(status_code=400, detail="No images uploaded.")

    saved_paths = []
    for file in files:
        file_path = os.path.join(UPLOAD_DIR, file.filename)

        # Save each uploaded image
        try:
            with open(file_path, "wb") as f:
                shutil.copyfileobj(file.file, f)
            logger.info(f"Received image: {file.filename} | Saved to {file_path}")
            saved_paths.append(file_path)
        except Exception as e:
            logger.error(f"Failed to save uploaded image {file.filename}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to save {file.filename}: {str(e)}")

    # Detect ingredients (FoodDetector now gets a list of image paths)
    try:
        ingredients = detector.detect_multiple(saved_paths)  # ✅ pass list, not str
        if not ingredients:
            logger.warning(f"No ingredients detected in {saved_paths}")
            raise HTTPException(status_code=404, detail="No ingredients detected in the uploaded images.")
        logger.info(f"Detected ingredients for {saved_paths}: {ingredients}")
    except Exception as e:
        logger.error(f"Error during detection: {e}")
        raise HTTPException(status_code=500, detail=f"Detection failed: {str(e)}")

    return {"ingredients": ingredients}
