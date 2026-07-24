from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.api import api_router
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
    """Root welcome endpoint redirecting to interactive documentation."""
    return {
        "message": "Welcome to DishGenie API! Access API documentation at /docs",
    }
