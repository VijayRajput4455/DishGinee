import json
from typing import Any

from app.core.config import settings


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
            print(f"[RabbitMQService] Published task '{task_type}' for Request #{payload.get('request_id')}")
            return True

        except ImportError:
            print(f"[RabbitMQService] Info: Pika package not loaded. Task '{task_type}' logged locally: {message}")
            return False
        except Exception as e:
            print(f"[RabbitMQService] Warning: Could not publish task to RabbitMQ ({e}). Task: {message}")
            return False
