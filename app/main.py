import os
import time
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.context import set_request_id
from app.core.database import Base, engine, get_database_status
from app.core.logger import get_logger, setup_logging
from app.core.metrics import metrics_endpoint, track_requests
from app.core.rate_limiter import rate_limit_middleware
import app.models  # Ensure all ORM models are registered
from app.schemas import ErrorDetail, ErrorResponse
from app.workers.consumer import get_worker_runtime_status, start_worker_in_background

# Initialize process-wide logging
setup_logging(level=settings.LOG_LEVEL, log_dir=settings.LOG_DIR, log_file=settings.LOG_FILE)
logger = get_logger(__name__)

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


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """Intercept HTTP request, set context request_id, and inject X-Request-ID response header."""
    rid = request.headers.get("X-Request-ID")
    request_id = set_request_id(rid)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.middleware("http")
async def metrics_and_rate_limit_middleware(request: Request, call_next):
    """Track request duration metrics and enforce IP rate limits."""
    start_time = time.time()
    try:
        # Check rate limits
        response = await rate_limit_middleware(request, call_next)
        process_time = time.time() - start_time
        track_requests(request, response, process_time)
        return response
    except HTTPException as exc:
        process_time = time.time() - start_time
        track_requests(request, exc, process_time)
        raise exc


# Exception Handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code >= 500:
        logger.error("HTTPException %s %s: %s", exc.status_code, request.url.path, exc.detail)
    elif exc.status_code >= 400:
        logger.warning("HTTPException %s %s: %s", exc.status_code, request.url.path, exc.detail)

    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            success=False,
            error=str(exc.detail),
            details=None,
        ).model_dump(mode="json"),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    details = [
        ErrorDetail(
            field=" -> ".join([str(loc) for loc in err["loc"]]),
            message=err["msg"],
        )
        for err in exc.errors()
    ]
    logger.warning("Validation error on %s %s: %s", request.method, request.url.path, details)
    error_payload = ErrorResponse(
        success=False,
        error="VALIDATION_ERROR",
        details=details,
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder(error_payload),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            success=False,
            error="INTERNAL_SERVER_ERROR",
            details=[ErrorDetail(field="server", message="An unexpected server error occurred.")],
        ).model_dump(mode="json"),
    )


# Register API v1 Routers
app.include_router(api_router, prefix="/api/v1")

# Mount Static Files for Frontend UI
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")


@app.on_event("startup")
def on_startup():
    """Ensure database connection is active, auto-create tables, and start worker if enabled."""
    ok, message = get_database_status()
    if ok:
        logger.info(message)
    else:
        logger.error(message)

    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database schema tables verified/created successfully.")
    except Exception as e:
        logger.warning("Could not auto-create database tables (%s).", e)

    if settings.AUTO_START_WORKER:
        started = start_worker_in_background()
        if started:
            logger.info("Embedded background RabbitMQ task worker started (AUTO_START_WORKER=true).")
        else:
            logger.info("Embedded background RabbitMQ task worker is already running.")


@app.get("/metrics", tags=["Metrics"])
async def get_metrics(request: Request):
    """Prometheus metrics scrape endpoint for monitoring dashboards."""
    return await metrics_endpoint(request)


@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint for Docker and monitoring services."""
    return {
        "status": "healthy",
        "service": "DishGenie API",
        "version": "1.0.0",
    }


@app.get("/worker-status", tags=["Worker Status"])
def worker_status_convenience():
    """Convenience root endpoint to query background task worker runtime status."""
    return get_worker_runtime_status()


@app.get("/", tags=["Root"])
def root():
    """Root welcome endpoint serving DishGenie Web UI console."""
    index_file = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(
            index_file,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )
    return {
        "message": "Welcome to DishGenie API! Access API documentation at /docs",
    }
