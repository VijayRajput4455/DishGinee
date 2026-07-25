from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.cuisine import Cuisine
from app.repositories.cuisine_repository import CuisineRepository
from app.schemas.cuisine import CuisineCreate, CuisineResponse, CuisineUpdate

router = APIRouter(prefix="/cuisines", tags=["Cuisines Management"])


@router.get("", response_model=dict, status_code=status.HTTP_200_OK)
def list_cuisines(db: Session = Depends(get_db)):
    """Fetch all active cuisines (automatically seeds defaults if empty)."""
    repo = CuisineRepository(db)
    items = repo.get_all_active()
    return {
        "success": True,
        "count": len(items),
        "data": [CuisineResponse.model_validate(c) for c in items],
    }


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_cuisine(payload: CuisineCreate, db: Session = Depends(get_db)):
    """Create a new cuisine style entry."""
    repo = CuisineRepository(db)
    existing = repo.get_by_name(payload.name)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cuisine '{payload.name}' already exists.",
        )

    new_obj = Cuisine(
        name=payload.name,
        emoji=payload.emoji,
        code=payload.code,
        description=payload.description,
        is_active=payload.is_active,
    )
    saved = repo.create(new_obj)
    return {
        "success": True,
        "message": f"Cuisine '{saved.name}' created successfully.",
        "data": CuisineResponse.model_validate(saved),
    }


@router.get("/{cuisine_id}", response_model=dict, status_code=status.HTTP_200_OK)
def get_cuisine(cuisine_id: int, db: Session = Depends(get_db)):
    """Get single cuisine details by ID."""
    repo = CuisineRepository(db)
    obj = repo.get_by_id(cuisine_id)
    if obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cuisine ID {cuisine_id} not found.",
        )
    return {"success": True, "data": CuisineResponse.model_validate(obj)}


@router.put("/{cuisine_id}", response_model=dict, status_code=status.HTTP_200_OK)
def update_cuisine(cuisine_id: int, payload: CuisineUpdate, db: Session = Depends(get_db)):
    """Update cuisine details by ID."""
    repo = CuisineRepository(db)
    obj = repo.get_by_id(cuisine_id)
    if obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cuisine ID {cuisine_id} not found.",
        )

    if payload.name is not None and payload.name != obj.name:
        dup = repo.get_by_name(payload.name)
        if dup is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cuisine name '{payload.name}' is already taken.",
            )
        obj.name = payload.name

    if payload.emoji is not None:
        obj.emoji = payload.emoji
    if payload.code is not None:
        obj.code = payload.code
    if payload.description is not None:
        obj.description = payload.description
    if payload.is_active is not None:
        obj.is_active = payload.is_active

    updated = repo.update(obj)
    return {
        "success": True,
        "message": f"Cuisine '{updated.name}' updated successfully.",
        "data": CuisineResponse.model_validate(updated),
    }


@router.delete("/{cuisine_id}", response_model=dict, status_code=status.HTTP_200_OK)
def delete_cuisine(cuisine_id: int, db: Session = Depends(get_db)):
    """Delete or soft-inactivate a cuisine by ID."""
    repo = CuisineRepository(db)
    obj = repo.get_by_id(cuisine_id)
    if obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cuisine ID {cuisine_id} not found.",
        )

    repo.delete(cuisine_id)
    return {
        "success": True,
        "message": f"Cuisine ID {cuisine_id} deleted successfully.",
    }
