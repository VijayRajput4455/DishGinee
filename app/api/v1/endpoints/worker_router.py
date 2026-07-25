from typing import Any

from fastapi import APIRouter

from app.workers.consumer import get_worker_runtime_status

router = APIRouter(prefix="/worker", tags=["Worker Status"])


@router.get("/status", summary="Get background worker execution and RabbitMQ connection status")
def get_status() -> dict[str, Any]:
    """Retrieve real-time thread health, state, and connectivity metrics of the RabbitMQ task worker."""
    return get_worker_runtime_status()
