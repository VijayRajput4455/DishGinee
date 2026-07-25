import os
from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.api import api_router
from app.core.database import engine
import app.models  # Ensure all ORM models are registered
from app.models.base import Base
from app.schemas import ErrorDetail, ErrorResponse

app = FastAPI(
    title="DishGenie API",
    description="Production-ready AI backend combining Computer Vision (YOLO), Audio AI (Whisper), and LLM Recipe Generation.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API v1 Routers
app.include_router(api_router, prefix="/api/v1")

# Mount Static Files for Frontend UI
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")


@app.on_event("startup")
def on_startup():
    """Ensure database tables are auto-created on server startup."""
    try:
        Base.metadata.create_all(bind=engine)
        print("[Startup] Database tables initialized successfully.")
    except Exception as e:
        print(f"[Startup] Note: Could not auto-create database tables ({e}).")


# Custom Exception Handler for Validation Errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    details = [
        ErrorDetail(
            field=" -> ".join([str(loc) for loc in err["loc"]]),
            message=err["msg"],
        )
        for err in exc.errors()
    ]
    error_payload = ErrorResponse(
        success=False,
        error="VALIDATION_ERROR",
        details=details,
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder(error_payload),
    )


@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint for Docker and monitoring services."""
    return {
        "status": "healthy",
        "service": "DishGenie API",
        "version": "1.0.0",
    }


@app.get("/", tags=["Root"])
def root():
    """Root welcome endpoint serving DishGenie Web UI console."""
    index_file = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(
            index_file,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )
    return {
        "message": "Welcome to DishGenie API! Access API documentation at /docs",
    }
