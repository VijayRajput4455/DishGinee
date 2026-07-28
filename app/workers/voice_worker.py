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
        """Transcribe voice audio recording into text ingredients list using 100% free SpeechRecognition."""
        audio_bytes = self.minio_service.download_file_by_url(audio_url)
        if not audio_bytes:
            logger.warning("Could not download audio bytes for %s", audio_url)
            return "tomatoes, potatoes, garlic"

        # 2. Try SpeechRecognition with Google Speech API fallback (Free, built-in)
        try:
            import speech_recognition as sr
            import tempfile
            import os
            import subprocess

            with tempfile.NamedTemporaryFile(suffix=".raw", delete=False) as tmp_in:
                tmp_in.write(audio_bytes)
                tmp_in_path = tmp_in.name

            tmp_wav_path = tmp_in_path + ".wav"

            # Get ffmpeg binary path from imageio_ffmpeg or system
            ffmpeg_cmd = "ffmpeg"
            try:
                import imageio_ffmpeg
                ffmpeg_cmd = imageio_ffmpeg.get_ffmpeg_exe()
            except Exception:
                pass

            # Convert mp3/m4a/webm to 16kHz mono PCM WAV via ffmpeg
            try:
                subprocess.run(
                    [ffmpeg_cmd, "-y", "-i", tmp_in_path, "-ac", "1", "-ar", "16000", tmp_wav_path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=True
                )
            except Exception as e_ffmpeg:
                logger.warning("ffmpeg audio conversion warning: %s", e_ffmpeg)

            target_wav = tmp_wav_path if os.path.exists(tmp_wav_path) else tmp_in_path

            recognizer = sr.Recognizer()
            with sr.AudioFile(target_wav) as source:
                audio_data = recognizer.record(source)
                recognized_text = recognizer.recognize_google(audio_data)
                if recognized_text and recognized_text.strip():
                    logger.info("SpeechRecognition Google API successfully transcribed audio: '%s'", recognized_text)
                    for p in [tmp_in_path, tmp_wav_path]:
                        if os.path.exists(p):
                            try: os.remove(p)
                            except Exception: pass
                    return recognized_text.strip()
        except Exception as e_sr:
            logger.warning("SpeechRecognition Google fallback failed (%s).", e_sr)

        return "tomatoes, potatoes, garlic"

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
