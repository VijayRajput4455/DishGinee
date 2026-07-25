from fastapi import APIRouter

from app.api.v1.endpoints.cuisine_router import router as cuisine_router
from app.api.v1.endpoints.request_router import router as request_router

api_router = APIRouter()
api_router.include_router(request_router)
api_router.include_router(cuisine_router)
