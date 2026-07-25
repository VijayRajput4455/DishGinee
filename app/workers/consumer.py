import json
import sys
import threading
import time
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.context import set_request_id
from app.core.database import SessionLocal
from app.core.logger import get_logger, setup_logging
from app.workers.cooking_guide_worker import CookingGuideWorker
from app.workers.image_worker import YOLOImageWorker
from app.workers.recipe_worker import LLMRecipeWorker
from app.workers.voice_worker import WhisperVoiceWorker

logger = get_logger(__name__)

_worker_thread: threading.Thread | None = None
_worker_lock = threading.Lock()
_worker_status_lock = threading.Lock()
_worker_status: dict[str, Any] = {
    "state": "idle",
    "connected": False,
    "last_error": None,
    "updated_at_epoch": time.time(),
}


def _set_worker_status(state: str, connected: bool, last_error: str | None = None) -> None:
    with _worker_status_lock:
        _worker_status["state"] = state
        _worker_status["connected"] = connected
        _worker_status["last_error"] = last_error
        _worker_status["updated_at_epoch"] = time.time()


def get_worker_runtime_status() -> dict[str, Any]:
    """Return thread-safe worker execution state and RabbitMQ metrics."""
    with _worker_status_lock:
        status = dict(_worker_status)

    status["thread_alive"] = _worker_thread is not None and _worker_thread.is_alive()
    status["auto_start_worker"] = settings.AUTO_START_WORKER
    status["queue_name"] = settings.RABBITMQ_QUEUE_NAME
    status["failed_queue_name"] = settings.RABBITMQ_FAILED_QUEUE_NAME
    status["rabbitmq_host"] = settings.RABBITMQ_HOST
    status["rabbitmq_port"] = settings.RABBITMQ_PORT
    return status


def _publish_retry(task_type: str, payload: dict[str, Any], error_message: str) -> None:
    """Re-publish failed task to queue with incremented retry count."""
    try:
        import pika

        retry_count = int(payload.get("retry_count", 0)) + 1
        payload["retry_count"] = retry_count
        payload["last_error"] = error_message

        message = {
            "task_type": task_type,
            "payload": payload,
        }

        credentials = pika.PlainCredentials(settings.RABBITMQ_USER, settings.RABBITMQ_PASSWORD)
        parameters = pika.ConnectionParameters(
            host=settings.RABBITMQ_HOST,
            port=settings.RABBITMQ_PORT,
            credentials=credentials,
        )
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()
        channel.queue_declare(queue=settings.RABBITMQ_QUEUE_NAME, durable=True)
        channel.basic_publish(
            exchange="",
            routing_key=settings.RABBITMQ_QUEUE_NAME,
            body=json.dumps(message),
            properties=pika.BasicProperties(delivery_mode=2, headers={"x-retry-count": retry_count}),
        )
        connection.close()
        logger.warning(
            "Requeued failed task '%s' (request_id=%s) retry=%s/%s",
            task_type,
            payload.get("request_id"),
            retry_count,
            settings.RABBITMQ_MAX_RETRIES,
        )
    except Exception as exc:
        logger.exception("Failed to publish retry task: %s", exc)


def _publish_failed(task_type: str, payload: dict[str, Any], error_message: str) -> None:
    """Publish task payload to dead-letter / failed queue after max retries exceeded."""
    try:
        import pika

        failed_payload = {
            "task_type": task_type,
            "payload": {
                **payload,
                "final_error": error_message,
                "status": "failed",
            },
        }

        credentials = pika.PlainCredentials(settings.RABBITMQ_USER, settings.RABBITMQ_PASSWORD)
        parameters = pika.ConnectionParameters(
            host=settings.RABBITMQ_HOST,
            port=settings.RABBITMQ_PORT,
            credentials=credentials,
        )
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()
        channel.queue_declare(queue=settings.RABBITMQ_FAILED_QUEUE_NAME, durable=True)
        channel.basic_publish(
            exchange="",
            routing_key=settings.RABBITMQ_FAILED_QUEUE_NAME,
            body=json.dumps(failed_payload),
            properties=pika.BasicProperties(delivery_mode=2, headers={"x-final-failure": True}),
        )
        connection.close()
        logger.error(
            "Sent task '%s' (request_id=%s) to failed queue '%s' after max retries",
            task_type,
            payload.get("request_id"),
            settings.RABBITMQ_FAILED_QUEUE_NAME,
        )
    except Exception as exc:
        logger.exception("Failed to publish task to failed queue: %s", exc)


class RabbitMQTaskConsumer:
    """RabbitMQ Background Worker Service listening to dishgenie_tasks queue."""

    def __init__(self) -> None:
        self.host = settings.RABBITMQ_HOST
        self.port = settings.RABBITMQ_PORT
        self.user = settings.RABBITMQ_USER
        self.password = settings.RABBITMQ_PASSWORD
        self.queue_name = settings.RABBITMQ_QUEUE_NAME

        # Initialize Workers
        self.image_worker = YOLOImageWorker()
        self.voice_worker = WhisperVoiceWorker()
        self.recipe_worker = LLMRecipeWorker()
        self.guide_worker = CookingGuideWorker()

    def process_message(self, body: bytes) -> bool:
        """Parse incoming RabbitMQ task message payload and route to appropriate worker."""
        db: Session = SessionLocal()
        try:
            message = json.loads(body.decode("utf-8"))
            task_type = message.get("task_type")
            payload = message.get("payload", {})
            request_id = str(payload.get("request_id", payload.get("x_request_id", "-")))

            # Set context request ID for log records
            set_request_id(request_id)
            retry_count = int(payload.get("retry_count", 0))

            logger.info("Received task '%s' for request_id=%s (retry=%s)", task_type, request_id, retry_count)

            success = False
            if task_type == "image.processing":
                success = self.image_worker.process_image_task(payload, db)
            elif task_type == "audio.transcription":
                success = self.voice_worker.process_voice_task(payload, db)
            elif task_type == "recipe.generation":
                success = self.recipe_worker.process_recipe_task(payload, db)
            elif task_type == "cooking_guide.generation":
                success = self.guide_worker.process_cooking_guide_task(payload, db)
            else:
                logger.warning("Unknown task_type '%s'", task_type)
                return True  # ack invalid message to discard

            if success:
                logger.info("Successfully processed task '%s' for request_id=%s", task_type, request_id)
            else:
                logger.error("Worker process returned False for task '%s' request_id=%s", task_type, request_id)
                self._handle_task_failure(task_type, payload, "Worker execution returned failure")

            return success
        except Exception as exc:
            logger.exception("Error processing worker task: %s", exc)
            try:
                msg_obj = json.loads(body.decode("utf-8"))
                self._handle_task_failure(
                    msg_obj.get("task_type", "unknown"),
                    msg_obj.get("payload", {}),
                    str(exc),
                )
            except Exception:
                pass
            return False
        finally:
            db.close()

    def _handle_task_failure(self, task_type: str, payload: dict[str, Any], error_message: str) -> None:
        retry_count = int(payload.get("retry_count", 0))
        max_retries = settings.RABBITMQ_MAX_RETRIES
        if retry_count < max_retries:
            _publish_retry(task_type, payload, error_message)
        else:
            _publish_failed(task_type, payload, error_message)

    def start(self) -> None:
        """Start listening continuously to RabbitMQ task queue."""
        setup_logging(settings.LOG_LEVEL, settings.LOG_DIR, settings.LOG_FILE)
        try:
            import pika
        except ImportError:
            logger.error("'pika' package not installed. Run: pip install pika")
            _set_worker_status("error", False, "'pika' package missing")
            return

        credentials = pika.PlainCredentials(self.user, self.password)
        parameters = pika.ConnectionParameters(
            host=self.host,
            port=self.port,
            credentials=credentials,
            heartbeat=600,
            blocked_connection_timeout=300,
        )

        logger.info(
            "Starting RabbitMQ Worker Consumer listening on host '%s:%s', queue '%s'...",
            self.host,
            self.port,
            self.queue_name,
        )
        _set_worker_status("starting", False)

        while True:
            try:
                connection = pika.BlockingConnection(parameters)
                channel = connection.channel()
                channel.queue_declare(queue=self.queue_name, durable=True)
                channel.basic_qos(prefetch_count=1)

                def callback(ch: Any, method: Any, properties: Any, body: bytes) -> None:
                    success = self.process_message(body)
                    # Always ack the original message; retries are handled via retry queues if failed
                    ch.basic_ack(delivery_tag=method.delivery_tag)

                channel.basic_consume(queue=self.queue_name, on_message_callback=callback)
                _set_worker_status("consuming", True)
                logger.info("RabbitMQ Worker Consumer active & consuming queue '%s'", self.queue_name)
                channel.start_consuming()

            except KeyboardInterrupt:
                _set_worker_status("stopped", False)
                logger.info("Stopping worker gracefully via KeyboardInterrupt.")
                sys.exit(0)
            except Exception as conn_err:
                _set_worker_status(
                    "disconnected",
                    False,
                    f"RabbitMQ unavailable at {self.host}:{self.port} ({conn_err})",
                )
                logger.warning(
                    "RabbitMQ connection lost (%s). Retrying connection in 5 seconds...",
                    conn_err,
                )
                time.sleep(5)


def start_worker_in_background() -> bool:
    """Start the worker in a daemon background thread once per process.

    Returns True if a new thread was started, False if already running.
    """
    global _worker_thread
    with _worker_lock:
        if _worker_thread is not None and _worker_thread.is_alive():
            return False

        def _worker_runner():
            consumer = RabbitMQTaskConsumer()
            consumer.start()

        _worker_thread = threading.Thread(
            target=_worker_runner,
            name="dishgenie-worker-thread",
            daemon=True,
        )
        _worker_thread.start()
        return True


if __name__ == "__main__":
    consumer = RabbitMQTaskConsumer()
    consumer.start()
