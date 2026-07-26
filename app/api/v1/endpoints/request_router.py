from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas import (
    APIResponse,
    DirectRecipeGuideRequest,
    RecipeRatingRequest,
    RecipeSelectRequest,
    RequestCreateText,
    RequestDetailResponse,
    RequestOutputResponse,
    RequestResponse,
)
from app.services.request_service import RequestService

router = APIRouter(prefix="/requests", tags=["Requests"])


@router.post(
    "/direct-guide",
    response_model=APIResponse[RequestOutputResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Get Direct Recipe Master Cooking Guide",
    description="Pass a dish name directly (e.g. Paneer Butter Masala) to bypass candidate selection and immediately return full step-by-step master cooking guide.",
)
def get_direct_recipe_guide(
    payload: DirectRecipeGuideRequest,
    db: Session = Depends(get_db),
):
    service = RequestService(db)
    result = service.create_direct_recipe_guide_request(
        recipe_title=payload.recipe_title,
        cuisine=payload.cuisine,
        is_vegetarian=payload.is_vegetarian,
    )
    return APIResponse(
        success=True,
        message=f"Master cooking guide for '{payload.recipe_title}' generated successfully.",
        data=result,
    )


@router.post(
    "/text",
    response_model=APIResponse[RequestResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Submit Text Ingredients",
    description="Submit a text ingredient list with an optional cuisine preference to generate 5 recipe options.",
)
def create_text_request(
    payload: RequestCreateText,
    db: Session = Depends(get_db),
):
    service = RequestService(db)
    result = service.create_text_request(raw_text_input=payload.raw_text_input, cuisine=payload.cuisine, is_vegetarian=payload.is_vegetarian)
    return APIResponse(
        success=True,
        message="Text request created successfully. Recipe generation task queued.",
        data=result,
    )


@router.post(
    "/image",
    response_model=APIResponse[RequestResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Upload Refrigerator/Food Image",
    description="Upload an image file and optional cuisine preference to detect ingredients using YOLO and generate recipes.",
)
def create_image_request(
    file: UploadFile,
    cuisine: str | None = Form(default=None, description="Optional cuisine preference (e.g. Indian, Italian, Mexican, Asian)"),
    is_vegetarian: bool | None = Form(default=None, description="Dietary preference constraint (true=Veg, false=Non-Veg, null=Any)"),
    db: Session = Depends(get_db),
):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Please upload an image file (JPEG, PNG).",
        )

    file_bytes = file.file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded image file is empty.",
        )

    service = RequestService(db)
    result = service.create_image_request(
        file_bytes=file_bytes,
        filename=file.filename or "image.jpg",
        cuisine=cuisine,
        is_vegetarian=is_vegetarian,
    )
    return APIResponse(
        success=True,
        message="Image request created successfully. Image processing task queued.",
        data=result,
    )


@router.post(
    "/voice",
    response_model=APIResponse[RequestResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Upload Voice Audio Recording",
    description="Upload a voice recording file and optional cuisine preference to transcribe ingredients using Whisper AI.",
)
def create_voice_request(
    file: UploadFile,
    cuisine: str | None = Form(default=None, description="Optional cuisine preference (e.g. Indian, Italian, Mexican, Asian)"),
    is_vegetarian: bool | None = Form(default=None, description="Dietary preference constraint (true=Veg, false=Non-Veg, null=Any)"),
    db: Session = Depends(get_db),
):
    file_bytes = file.file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded audio file is empty.",
        )

    service = RequestService(db)
    result = service.create_voice_request(
        file_bytes=file_bytes,
        filename=file.filename or "audio.wav",
        cuisine=cuisine,
        is_vegetarian=is_vegetarian,
    )
    return APIResponse(
        success=True,
        message="Voice request created successfully. Transcription task queued.",
        data=result,
    )


@router.get(
    "/popular",
    summary="Get Most Popular & High-Rated Recipes",
    description="Retrieve top rated and most popular recipes from PostgreSQL database.",
)
def get_popular_recipes(
    limit: int = 6,
    db: Session = Depends(get_db),
):
    service = RequestService(db)
    popular = service.get_popular_recipes(limit=limit)
    return APIResponse(
        success=True,
        message="Popular recipes retrieved successfully.",
        data=popular,
    )


@router.get(
    "/stats",
    summary="Get Database Request Metrics & Stats",
    description="Retrieve live PostgreSQL database metrics including total requests, completed count, in-progress count, and total recipes generated.",
)
def get_request_stats(
    db: Session = Depends(get_db),
):
    service = RequestService(db)
    stats = service.get_stats()
    return APIResponse(
        success=True,
        message="Live database stats retrieved successfully.",
        data=stats,
    )


@router.get(
    "/{request_id}",
    response_model=APIResponse[RequestDetailResponse],
    summary="Get Request Details",
    description="Retrieve request metadata, images with presigned URLs, and generated recipe guides.",
)
def get_request_details(
    request_id: int,
    db: Session = Depends(get_db),
):
    service = RequestService(db)
    result = service.get_request_details(request_id=request_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Request #{request_id} not found.",
        )

    return APIResponse(
        success=True,
        message="Request details retrieved successfully.",
        data=result,
    )


@router.post(
    "/{request_id}/select-recipe",
    response_model=APIResponse[RequestOutputResponse],
    summary="Select Recipe Choice",
    description="Select a candidate recipe title from Stage 1 options to generate full Stage 2 cooking guide.",
)
def select_recipe(
    request_id: int,
    payload: RecipeSelectRequest,
    db: Session = Depends(get_db),
):
    service = RequestService(db)

    # Check request exists
    request_details = service.get_request_details(request_id)
    if request_details is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Request #{request_id} not found.",
        )

    result = service.select_recipe(request_id=request_id, recipe_title=payload.recipe_title)
    return APIResponse(
        success=True,
        message=f"Recipe '{payload.recipe_title}' selected. Stage 2 cooking guide task queued.",
        data=result,
    )


@router.post(
    "/{request_id}/rate",
    response_model=APIResponse[RequestOutputResponse],
    summary="Rate Recipe",
    description="Submit user star rating (1 to 5 stars) and feedback comment to save directly into PostgreSQL DB.",
)
def rate_recipe(
    request_id: int,
    payload: RecipeRatingRequest,
    db: Session = Depends(get_db),
):
    service = RequestService(db)
    result = service.rate_request(request_id=request_id, rating=payload.rating, comment=payload.comment)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Request #{request_id} not found.",
        )
    return APIResponse(
        success=True,
        message=f"Rating of {payload.rating} stars saved successfully to PostgreSQL database!",
        data=result,
    )
