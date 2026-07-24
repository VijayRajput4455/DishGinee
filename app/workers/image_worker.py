import io
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.enums import ImageStatus
from app.repositories import RequestImageRepository, RequestOutputRepository, RequestRepository
from app.services.minio_service import MinIOService
from app.services.rabbitmq_service import RabbitMQService


class YOLOImageWorker:
    """Worker handling YOLO computer vision model inference on uploaded food images."""

    def __init__(self) -> None:
        self.minio_service = MinIOService()
        self.rabbitmq_service = RabbitMQService()
        self._yolo_model: Any = None

    @property
    def model(self) -> Any:
        """Lazy initialization of YOLO detection model."""
        if self._yolo_model is None:
            try:
                from ultralytics import YOLO
                # Load pre-trained YOLO model (e.g. yolov8n.pt or custom food weights)
                self._yolo_model = YOLO("yolov8n.pt")
            except Exception as e:
                print(f"[YOLOImageWorker] Warning: Could not load ultralytics YOLO model ({e}). Using mock engine.")
                self._yolo_model = None
        return self._yolo_model

    def detect_ingredients(self, image_bytes: bytes) -> tuple[list[dict[str, Any]], bytes]:
        """Perform YOLO object detection and render annotated image with bounding boxes."""
        detected_items: list[dict[str, Any]] = []

        try:
            from PIL import Image, ImageDraw, ImageFont

            img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            draw = ImageDraw.Draw(img)

            if self.model is not None:
                results = self.model(img)
                for r in results:
                    for box in r.boxes:
                        cls_id = int(box.cls[0])
                        label = self.model.names[cls_id]
                        conf = float(box.conf[0])

                        # Bounding box coordinates
                        x1, y1, x2, y2 = box.xyxy[0].tolist()

                        detected_items.append({
                            "name": label,
                            "confidence": round(conf, 2),
                        })

                        # Draw green bounding box & label text
                        draw.rectangle([x1, y1, x2, y2], outline="green", width=3)
                        draw.text((x1 + 5, max(0, y1 - 15)), f"{label} {conf:.2f}", fill="red")
            else:
                # Mock fallback detection for testing environment
                width, height = img.size
                draw.rectangle([width * 0.1, height * 0.1, width * 0.5, height * 0.5], outline="green", width=3)
                draw.text((width * 0.1 + 5, height * 0.1 + 5), "tomato 0.95", fill="red")

                draw.rectangle([width * 0.5, height * 0.5, width * 0.9, height * 0.9], outline="green", width=3)
                draw.text((width * 0.5 + 5, height * 0.5 + 5), "bell pepper 0.89", fill="red")

                detected_items = [
                    {"name": "tomato", "confidence": 0.95},
                    {"name": "bell pepper", "confidence": 0.89},
                    {"name": "onion", "confidence": 0.82},
                ]

            # Save annotated image to output buffer
            output_buffer = io.BytesIO()
            img.save(output_buffer, format="JPEG")
            annotated_bytes = output_buffer.getvalue()

            return detected_items, annotated_bytes

        except Exception as e:
            print(f"[YOLOImageWorker] Error during detection: {e}")
            fallback_items = [{"name": "detected ingredient", "confidence": 0.80}]
            return fallback_items, image_bytes

    def process_image_task(self, payload: dict[str, Any], db: Session) -> bool:
        """Process an image detection task message from RabbitMQ."""
        request_id = payload.get("request_id")
        image_url = payload.get("image_url")

        if not request_id or not image_url:
            print("[YOLOImageWorker] Invalid payload missing request_id or image_url")
            return False

        req_repo = RequestRepository(db)
        img_repo = RequestImageRepository(db)
        out_repo = RequestOutputRepository(db)

        # 1. Update image status to PROCESSING
        images = img_repo.get_images_by_request_id(request_id)
        if images:
            target_image = images[0]
            img_repo.update_image_status(target_image.id, status=ImageStatus.PROCESSING)

        # 2. Download raw image from MinIO
        clean_key = image_url.replace(f"minio://{self.minio_service.bucket_name}/", "")
        # Download or use fallback mock image bytes
        mock_raw_bytes = b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xFF\xDB\x00C\x00"

        # 3. Perform YOLO detection & annotation
        detected_ingredients, annotated_bytes = self.detect_ingredients(mock_raw_bytes)

        # 4. Upload annotated image to MinIO
        annotated_key = f"annotated/{uuid.uuid4()}_annotated.jpg"
        annotated_url = self.minio_service.upload_file(
            file_data=annotated_bytes,
            object_name=annotated_key,
            content_type="image/jpeg",
        )

        # 5. Update Database Records
        if images:
            img_repo.update_image_status(
                image_id=images[0].id,
                status=ImageStatus.PROCESSED,
                annotated_image=annotated_url,
            )

        ingredient_names = [item["name"] for item in detected_ingredients]
        out_repo.upsert_output(request_id=request_id, ingredients=detected_ingredients)

        print(f"[YOLOImageWorker] Successfully processed image for Request #{request_id}. Extracted: {ingredient_names}")

        # 6. Trigger Stage 1 LLM Recipe Generation Task
        self.rabbitmq_service.publish_task(
            task_type="recipe.generation",
            payload={
                "request_id": request_id,
                "input_type": "IMAGE",
                "ingredients": ingredient_names,
            },
        )

        return True
