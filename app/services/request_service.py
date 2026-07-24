import uuid
from typing import Any

from sqlalchemy.orm import Session

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
        """Create a text ingredient request with optional cuisine and publish recipe generation task."""
        request_obj = self.req_repo.create_request(
            input_type=InputType.TEXT,
            raw_text_input=raw_text_input,
            cuisine=cuisine,
        )

        # Publish task to RabbitMQ for LLM Stage 1 recipe generation
        self.rabbitmq_service.publish_task(
            task_type="recipe.generation",
            payload={
                "request_id": request_obj.id,
                "input_type": InputType.TEXT.value,
                "text": raw_text_input,
                "cuisine": cuisine,
            },
        )

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

        return RequestResponse.model_validate(request_obj)

    def get_request_details(self, request_id: int) -> RequestDetailResponse | None:
        """Fetch request details with presigned URLs for image rendering."""
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

        return response

    def select_recipe(self, request_id: int, recipe_title: str) -> RequestOutputResponse:
        """Select a recipe option and trigger LLM Stage 2 Cooking Guide generation."""
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

        return RequestOutputResponse.model_validate(output_obj)
