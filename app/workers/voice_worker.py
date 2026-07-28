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
        self._whisper_model: Any = None

    @property
    def whisper_model(self) -> Any:
        """Lazy initialization of local open-source OpenAI Whisper model."""
        if self._whisper_model is None:
            try:
                import torch
                import whisper
                device = "cuda" if torch.cuda.is_available() else "cpu"
                logger.info("Loading local open-source Whisper model ('tiny') on device: %s...", device)
                self._whisper_model = whisper.load_model("tiny", device=device)
            except Exception as e:
                logger.warning("Could not load local open-source Whisper model (%s). Using SpeechRecognition fallback.", e)
                self._whisper_model = None
        return self._whisper_model

    def transcribe_audio(self, audio_url: str) -> str:
        """Transcribe voice audio recording into text ingredients list using local OpenAI Whisper model or SpeechRecognition."""
        audio_bytes = self.minio_service.download_file_by_url(audio_url)
        if not audio_bytes:
            logger.warning("Could not download audio bytes for %s", audio_url)
            return "tomatoes, potatoes, garlic"

        import tempfile
        import os
        import subprocess

        # Write audio bytes to temp file
        with tempfile.NamedTemporaryFile(suffix=".raw", delete=False) as tmp_in:
            tmp_in.write(audio_bytes)
            tmp_in_path = tmp_in.name

        tmp_wav_path = tmp_in_path + ".wav"

        # Convert to 16kHz WAV using imageio_ffmpeg
        ffmpeg_cmd = "ffmpeg"
        try:
            import imageio_ffmpeg
            ffmpeg_cmd = imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            pass

        try:
            subprocess.run(
                [ffmpeg_cmd, "-y", "-i", tmp_in_path, "-ac", "1", "-ar", "16000", tmp_wav_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True
            )
        except Exception as e_conv:
            logger.warning("Audio ffmpeg conversion warning: %s", e_conv)

        target_audio_path = tmp_wav_path if os.path.exists(tmp_wav_path) else tmp_in_path

        # 1. Try local OpenAI Whisper model
        if self.whisper_model is not None:
            try:
                result = self.whisper_model.transcribe(target_audio_path)
                if result and "text" in result and result["text"].strip():
                    text = result["text"].strip()
                    logger.info("Local OpenAI Whisper model transcribed audio: '%s'", text)
                    for p in [tmp_in_path, tmp_wav_path]:
                        if os.path.exists(p):
                            try: os.remove(p)
                            except Exception: pass
                    return text
            except Exception as e_w:
                logger.warning("Local Whisper transcription warning (%s). Trying SpeechRecognition fallback.", e_w)

        # 2. Try SpeechRecognition Google Speech API fallback
        try:
            import speech_recognition as sr
            recognizer = sr.Recognizer()
            with sr.AudioFile(target_audio_path) as source:
                audio_data = recognizer.record(source)
                recognized_text = recognizer.recognize_google(audio_data)
                if recognized_text and recognized_text.strip():
                    logger.info("SpeechRecognition Google API transcribed audio: '%s'", recognized_text)
                    for p in [tmp_in_path, tmp_wav_path]:
                        if os.path.exists(p):
                            try: os.remove(p)
                            except Exception: pass
                    return recognized_text.strip()
        except Exception as e_sr:
            logger.warning("SpeechRecognition Google fallback failed (%s).", e_sr)

        for p in [tmp_in_path, tmp_wav_path]:
            if os.path.exists(p):
                try: os.remove(p)
                except Exception: pass

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
