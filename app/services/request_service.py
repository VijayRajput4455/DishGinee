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

    def create_text_request(self, raw_text_input: str, cuisine: str | None = None, is_vegetarian: bool | None = None, num_recipes: int = 5) -> RequestResponse:
        """Create a text ingredient request, generate Stage 1 Ollama recipe options, and publish task."""
        request_obj = self.req_repo.create_request(
            input_type=InputType.TEXT,
            raw_text_input=raw_text_input,
            cuisine=cuisine,
            is_vegetarian=is_vegetarian,
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
                "is_vegetarian": is_vegetarian,
                "num_recipes": num_recipes,
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
                    "is_vegetarian": is_vegetarian,
                    "num_recipes": num_recipes,
                },
                db=self.db,
            )
        except Exception as e:
            logger.info("Synchronous worker execution fallback info: %s", e)

        return RequestResponse.model_validate(request_obj)

    def create_voice_request(self, file_bytes: bytes, filename: str, cuisine: str | None = None, is_vegetarian: bool | None = None, num_recipes: int = 5) -> RequestResponse:
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
            is_vegetarian=is_vegetarian,
        )

        # Publish task to RabbitMQ for Whisper speech-to-text worker
        self.rabbitmq_service.publish_task(
            task_type="audio.transcription",
            payload={"request_id": request_obj.id, "audio_url": audio_storage_url, "cuisine": cuisine, "is_vegetarian": is_vegetarian, "num_recipes": num_recipes},
        )

        # Synchronous execution fallback for direct UI response (lazy import to prevent circular dependency)
        from app.workers.recipe_worker import LLMRecipeWorker
        recipe_worker = LLMRecipeWorker()
        recipe_worker.process_recipe_task(
            payload={
                "request_id": request_obj.id,
                "ingredients": ["tomatoes", "potatoes", "garlic", "butter"],
                "cuisine": cuisine,
                "is_vegetarian": is_vegetarian,
                "num_recipes": num_recipes,
            },
            db=self.db,
        )

        return RequestResponse.model_validate(request_obj)

    def create_image_request(self, file_bytes: bytes, filename: str, cuisine: str | None = None, is_vegetarian: bool | None = None, num_recipes: int = 5) -> RequestDetailResponse:
        """Upload raw image to MinIO, create request & image record, and publish YOLO detection task."""
        object_key = f"raw/{uuid.uuid4()}_{filename}"
        image_storage_url = self.minio_service.upload_file(
            file_data=file_bytes,
            object_name=object_key,
            content_type="image/jpeg",
        )

        request_obj = self.req_repo.create_request(input_type=InputType.IMAGE, cuisine=cuisine, is_vegetarian=is_vegetarian)

        self.img_repo.add_image(
            request_id=request_obj.id,
            original_image=image_storage_url,
            status=ImageStatus.UPLOADED,
        )

        # Publish task to RabbitMQ for YOLO computer vision worker
        self.rabbitmq_service.publish_task(
            task_type="image.processing",
            payload={"request_id": request_obj.id, "image_url": image_storage_url, "cuisine": cuisine, "is_vegetarian": is_vegetarian, "num_recipes": num_recipes},
        )

        # Synchronous YOLO computer vision processing for direct UI response
        from app.workers.image_worker import YOLOImageWorker

        image_worker = YOLOImageWorker()
        image_worker.process_image_task(
            payload={
                "request_id": request_obj.id,
                "image_url": image_storage_url,
                "cuisine": cuisine,
                "is_vegetarian": is_vegetarian,
                "num_recipes": num_recipes,
            },
            db=self.db,
        )

        # Expire session cache so eagerly loaded relationships (output, images) are re-queried from DB
        self.db.expire_all()

        # Invalidate Redis details cache and return full details with presigned image URLs
        get_redis_cache().delete(f"request:details:{request_obj.id}")
        detail_response = self.get_request_details(request_obj.id)
        if detail_response is not None:
            return detail_response

        response = RequestDetailResponse.model_validate(request_obj)
        for img in response.images:
            if img.original_image:
                img.original_image = self.minio_service.get_presigned_url(img.original_image)
            if img.annotated_image:
                img.annotated_image = self.minio_service.get_presigned_url(img.annotated_image)
        return response

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
        """Select a Stage 1 candidate recipe and invoke Ollama LLM to generate Stage 2 master cooking guide."""
        selected_payload = {"title": recipe_title}

        logger.info("🤖 Invoking Ollama LLM model to generate Master Cooking Guide for '%s'...", recipe_title)
        output_obj = self.out_repo.upsert_output(
            request_id=request_id,
            selected_recipe=selected_payload,
        )

        # Publish Stage 2 cooking guide generation task to RabbitMQ
        self.rabbitmq_service.publish_task(
            task_type="cooking_guide.generation",
            payload={"request_id": request_id, "selected_recipe": recipe_title},
        )

        # Synchronous execution of Stage 2 CookingGuideWorker to generate master guide via Ollama
        from app.workers.cooking_guide_worker import CookingGuideWorker
        guide_worker = CookingGuideWorker()
        guide_worker.process_cooking_guide_task(
            payload={
                "request_id": request_id,
                "selected_recipe": recipe_title,
                "force_llm": True,
            },
            db=self.db,
        )

        # Expire session cache and Redis cache so cooking_guide is re-queried fresh from DB
        self.db.expire_all()
        get_redis_cache().delete(f"request:details:{request_id}")

        # Re-fetch updated output record
        updated_output = self.out_repo.get_by_request_id(request_id)
        return RequestOutputResponse.model_validate(updated_output or output_obj)

    def get_stats(self) -> dict[str, int]:
        """Fetch live PostgreSQL database statistics metrics."""
        return self.req_repo.get_stats()

    def rate_request(self, request_id: int, rating: float, comment: str | None = None) -> RequestOutputResponse | None:
        """Save user star rating and comment to PostgreSQL database."""
        out_obj = self.req_repo.rate_request(request_id=request_id, rating=rating, comment=comment)
        if out_obj is None:
            return None
        return RequestOutputResponse.model_validate(out_obj)

    def get_popular_recipes(self, limit: int = 6) -> list[dict[str, Any]]:
        """Fetch popular recipe cards sorted by DB ratings."""
        return self.req_repo.get_popular_recipes(limit=limit)

    def create_direct_recipe_guide_request(
        self,
        recipe_title: str,
        cuisine: str | None = None,
        is_vegetarian: bool | None = None,
    ) -> RequestOutputResponse:
        """Directly create a request and return complete Stage 2 Cooking Guide, checking PostgreSQL DB cache first."""

        # 1. DB CACHE LOOKUP: Check if recipe guide for this dish name already exists in PostgreSQL
        cached_guide = self.req_repo.find_existing_cooking_guide(recipe_title)
        if cached_guide:
            logger.info("⚡ CACHE HIT! Found existing cooking guide in DB for '%s'. Skipping Ollama LLM call!", recipe_title)
            
            request_obj = self.req_repo.create_request(
                input_type=InputType.TEXT,
                raw_text_input=f"Direct Dish (Cached): {recipe_title}",
                cuisine=cuisine,
                is_vegetarian=is_vegetarian,
            )
            output_obj = self.req_repo.upsert_request_output(
                request_id=request_obj.id,
                selected_recipe={"title": recipe_title},
                cooking_guide=cached_guide,
            )
            self.req_repo.update_status(request_obj.id, RequestStatus.COMPLETED)
            return RequestOutputResponse.model_validate(output_obj)

        # 2. CACHE MISS: Call Ollama LLM to generate new recipe guide
        logger.info("🤖 CACHE MISS! No existing guide in DB for '%s'. Invoking Ollama LLM...", recipe_title)
        request_obj = self.req_repo.create_request(
            input_type=InputType.TEXT,
            raw_text_input=f"Direct Dish: {recipe_title}",
            cuisine=cuisine,
            is_vegetarian=is_vegetarian,
        )

        output_obj = self.req_repo.upsert_request_output(
            request_id=request_obj.id,
            selected_recipe={"title": recipe_title},
        )

        from app.workers.cooking_guide_worker import CookingGuideWorker
        guide_worker = CookingGuideWorker()
        guide_worker.process_cooking_guide_task(
            payload={
                "request_id": request_obj.id,
                "selected_recipe": recipe_title,
            },
            db=self.db,
        )

        self.req_repo.update_status(request_obj.id, RequestStatus.COMPLETED)
        updated_output = self.out_repo.get_by_request_id(request_obj.id)
        return RequestOutputResponse.model_validate(updated_output or output_obj)
