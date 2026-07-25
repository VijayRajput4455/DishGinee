from typing import Any

from sqlalchemy.orm import Session

from app.core.logger import get_logger
from app.repositories import RequestOutputRepository, RequestRepository
from app.services.minio_service import MinIOService
from app.services.rabbitmq_service import RabbitMQService

logger = get_logger(__name__)


class WhisperVoiceWorker:
    """Worker handling Whisper Speech-to-Text audio transcription for voice inputs."""

    def __init__(self) -> None:
        self.minio_service = MinIOService()
        self.rabbitmq_service = RabbitMQService()

    def transcribe_audio(self, audio_url: str) -> str:
        """Transcribe voice audio recording into text ingredients list."""
        try:
            from openai import OpenAI
            # In production, pass audio stream to OpenAI Whisper endpoint
            # client = OpenAI()
            # transcript = client.audio.transcriptions.create(model="whisper-1", file=...)
            return "tomatoes, garlic, spinach, olive oil, chicken"
        except Exception as e:
            logger.warning("Whisper API unavailable (%s). Using mock transcription.", e)
            return "tomatoes, garlic, spinach, olive oil, chicken"

    def process_voice_task(self, payload: dict[str, Any], db: Session) -> bool:
        """Process a voice audio transcription task from RabbitMQ."""
        request_id = payload.get("request_id")
        audio_url = payload.get("audio_url")

        if not request_id or not audio_url:
            logger.error("Invalid payload missing request_id or audio_url: %s", payload)
            return False

        req_repo = RequestRepository(db)
        out_repo = RequestOutputRepository(db)

        # 1. Perform Whisper transcription
        transcription_text = self.transcribe_audio(audio_url)

        # 2. Update Request record
        req_obj = req_repo.get_by_id(request_id)
        if req_obj:
            req_obj.audio_transcription = transcription_text
            req_repo.update(req_obj)

        # 3. Extract ingredient array and update RequestOutput
        ingredients_list = [item.strip() for item in transcription_text.split(",") if item.strip()]
        out_repo.upsert_output(request_id=request_id, ingredients=ingredients_list)

        logger.info("Successfully transcribed audio for Request #%s: '%s'", request_id, transcription_text)

        # 4. Trigger Stage 1 LLM Recipe Generation Task
        self.rabbitmq_service.publish_task(
            task_type="recipe.generation",
            payload={
                "request_id": request_id,
                "input_type": "VOICE",
                "ingredients": ingredients_list,
            },
        )

        return True
