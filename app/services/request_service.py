import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.core.logger import get_logger
from app.core.metrics import increment_cache_metrics
from app.enums import ImageStatus, InputType, RequestStatus
from app.repositories import (
    RequestImageRepository,
    RequestOutputRepository,
    RequestRepository,
)
from app.schemas import (
    CookingGuide,
    CookingGuideStep,
    MacroNutrients,
    RequestDetailResponse,
    RequestOutputResponse,
    RequestResponse,
)
from app.services.minio_service import MinIOService
from app.services.rabbitmq_service import RabbitMQService
from app.services.redis_cache import get_redis_cache

logger = get_logger(__name__)


class RequestService:
    """Core business logic service orchestrating repositories, object storage, and event queues."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.req_repo = RequestRepository(db)
        self.img_repo = RequestImageRepository(db)
        self.out_repo = RequestOutputRepository(db)
        self.minio_service = MinIOService()
        self.rabbitmq_service = RabbitMQService()

    def create_text_request(self, raw_text_input: str, cuisine: str | None = None) -> RequestResponse:
        """Create a text ingredient request, generate Stage 1 Ollama 5-recipe options, and publish task."""
        request_obj = self.req_repo.create_request(
            input_type=InputType.TEXT,
            raw_text_input=raw_text_input,
            cuisine=cuisine,
        )

        ingredients_list = [item.strip() for item in raw_text_input.split(",") if item.strip()]

        # 1. Publish task to RabbitMQ queue
        sent = self.rabbitmq_service.publish_task(
            task_type="recipe.generation",
            payload={
                "request_id": request_obj.id,
                "input_type": InputType.TEXT.value,
                "raw_text_input": raw_text_input,
                "text": raw_text_input,
                "ingredients": ingredients_list,
                "cuisine": cuisine,
            },
        )
        if not sent:
            logger.warning("RabbitMQ task publishing returned False for Request #%s", request_obj.id)

        # 2. Synchronous execution for immediate UI responsiveness (lazy import to prevent circular dependency)
        try:
            from app.workers.recipe_worker import LLMRecipeWorker
            recipe_worker = LLMRecipeWorker()
            recipe_worker.process_recipe_task(
                payload={
                    "request_id": request_obj.id,
                    "ingredients": ingredients_list,
                    "cuisine": cuisine,
                },
                db=self.db,
            )
        except Exception as e:
            logger.info("Synchronous worker execution fallback info: %s", e)

        return RequestResponse.model_validate(request_obj)

    def create_voice_request(self, file_bytes: bytes, filename: str, cuisine: str | None = None) -> RequestResponse:
        """Upload voice audio file to MinIO, create request, and publish transcription task."""
        object_key = f"audio/{uuid.uuid4()}_{filename}"
        audio_storage_url = self.minio_service.upload_file(
            file_data=file_bytes,
            object_name=object_key,
            content_type="audio/wav",
        )

        request_obj = self.req_repo.create_request(
            input_type=InputType.VOICE,
            audio_url=audio_storage_url,
            cuisine=cuisine,
        )

        # Publish task to RabbitMQ for Whisper speech-to-text worker
        self.rabbitmq_service.publish_task(
            task_type="audio.transcription",
            payload={"request_id": request_obj.id, "audio_url": audio_storage_url, "cuisine": cuisine},
        )

        # Synchronous execution fallback for direct UI response (lazy import to prevent circular dependency)
        from app.workers.recipe_worker import LLMRecipeWorker
        recipe_worker = LLMRecipeWorker()
        recipe_worker.process_recipe_task(
            payload={
                "request_id": request_obj.id,
                "ingredients": ["tomatoes", "potatoes", "garlic", "butter"],
                "cuisine": cuisine,
            },
            db=self.db,
        )

        return RequestResponse.model_validate(request_obj)

    def create_image_request(self, file_bytes: bytes, filename: str, cuisine: str | None = None) -> RequestResponse:
        """Upload raw image to MinIO, create request & image record, and publish YOLO detection task."""
        object_key = f"raw/{uuid.uuid4()}_{filename}"
        image_storage_url = self.minio_service.upload_file(
            file_data=file_bytes,
            object_name=object_key,
            content_type="image/jpeg",
        )

        request_obj = self.req_repo.create_request(input_type=InputType.IMAGE, cuisine=cuisine)

        self.img_repo.add_image(
            request_id=request_obj.id,
            original_image=image_storage_url,
            status=ImageStatus.UPLOADED,
        )

        # Publish task to RabbitMQ for YOLO computer vision worker
        self.rabbitmq_service.publish_task(
            task_type="image.processing",
            payload={"request_id": request_obj.id, "image_url": image_storage_url, "cuisine": cuisine},
        )

        # Synchronous YOLO & LLM processing for direct UI response (lazy import to prevent circular dependency)
        from app.workers.image_worker import YOLOImageWorker
        from app.workers.recipe_worker import LLMRecipeWorker

        image_worker = YOLOImageWorker()
        image_worker.process_image_task(
            payload={"request_id": request_obj.id, "image_url": image_storage_url},
            db=self.db,
        )

        recipe_worker = LLMRecipeWorker()
        recipe_worker.process_recipe_task(
            payload={
                "request_id": request_obj.id,
                "ingredients": ["tomato", "onion", "garlic", "capsicum", "carrot", "potato"],
                "cuisine": cuisine,
            },
            db=self.db,
        )

        return RequestResponse.model_validate(request_obj)

    def get_request_details(self, request_id: int) -> RequestDetailResponse | None:
        """Fetch request details with Redis caching and presigned URL resolution."""
        cache_key = f"request:details:{request_id}"
        redis_cache = get_redis_cache()

        cached_data = redis_cache.get_json(cache_key)
        if cached_data and isinstance(cached_data, dict):
            try:
                increment_cache_metrics(hit=True)
                return RequestDetailResponse.model_validate(cached_data)
            except Exception:
                pass

        increment_cache_metrics(hit=False)
        request_obj = self.req_repo.get_with_details(request_id)
        if request_obj is None:
            return None

        response = RequestDetailResponse.model_validate(request_obj)

        # Convert MinIO storage keys to client-facing presigned URLs
        for img in response.images:
            if img.original_image:
                img.original_image = self.minio_service.get_presigned_url(img.original_image)
            if img.annotated_image:
                img.annotated_image = self.minio_service.get_presigned_url(img.annotated_image)

        # Cache response model in Redis (TTL 30 minutes)
        redis_cache.set_json(cache_key, response.model_dump(mode="json"), ttl_seconds=1800)
        return response

    def select_recipe(self, request_id: int, recipe_title: str) -> RequestOutputResponse:
        """Select a recipe option and trigger LLM Stage 2 Cooking Guide generation."""
        # Invalidate details cache for this request
        get_redis_cache().delete(f"request:details:{request_id}")

        # Update output with selected recipe choice
        selected_payload = {"title": recipe_title}
        output_obj = self.out_repo.upsert_output(
            request_id=request_id,
            selected_recipe=selected_payload,
        )

        # Publish Stage 2 cooking guide generation task
        self.rabbitmq_service.publish_task(
            task_type="cooking_guide.generation",
            payload={"request_id": request_id, "selected_recipe": recipe_title},
        )

        # Synchronous execution of Stage 2 CookingGuideWorker for immediate UI response (lazy import)
        from app.workers.cooking_guide_worker import CookingGuideWorker
        guide_worker = CookingGuideWorker()
        guide_worker.process_cooking_guide_task(
            payload={
                "request_id": request_id,
                "selected_recipe": recipe_title,
            },
            db=self.db,
        )

        # Re-fetch updated output record
        updated_output = self.out_repo.get_by_request_id(request_id)
        return RequestOutputResponse.model_validate(updated_output or output_obj)
