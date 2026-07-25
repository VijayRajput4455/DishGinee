import json
from typing import Any

from app.core.config import settings
from app.core.context import get_request_id
from app.core.logger import get_logger

logger = get_logger(__name__)


class RabbitMQService:
    """Service handling message publishing to RabbitMQ queues."""

    def __init__(self) -> None:
        self.host = settings.RABBITMQ_HOST
        self.port = settings.RABBITMQ_PORT
        self.user = settings.RABBITMQ_USER
        self.password = settings.RABBITMQ_PASSWORD
        self.queue_name = settings.RABBITMQ_QUEUE_NAME

    def publish_task(self, task_type: str, payload: dict[str, Any]) -> bool:
        """Publish a JSON task payload to the RabbitMQ queue."""
        # Ensure context request_id is present in payload
        if "request_id" not in payload and get_request_id() != "-":
            payload["request_id"] = get_request_id()

        message = {
            "task_type": task_type,
            "payload": payload,
        }

        try:
            import pika

            credentials = pika.PlainCredentials(self.user, self.password)
            parameters = pika.ConnectionParameters(
                host=self.host,
                port=self.port,
                credentials=credentials,
                connection_attempts=3,
                retry_delay=1,
            )

            connection = pika.BlockingConnection(parameters)
            channel = connection.channel()

            # Declare durable queue
            channel.queue_declare(queue=self.queue_name, durable=True)

            # Publish persistent message
            channel.basic_publish(
                exchange="",
                routing_key=self.queue_name,
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Make message persistent
                    content_type="application/json",
                ),
            )

            connection.close()
            logger.info("Published task '%s' for Request #%s", task_type, payload.get("request_id"))
            return True

        except ImportError:
            logger.info("Pika package not loaded. Task '%s' logged locally: %s", task_type, message)
            return False
        except Exception as e:
            logger.warning("Could not publish task '%s' to RabbitMQ (%s). Payload: %s", task_type, e, message)
            return False
