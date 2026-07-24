import json
import sys
import time
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.workers.cooking_guide_worker import CookingGuideWorker
from app.workers.image_worker import YOLOImageWorker
from app.workers.recipe_worker import LLMRecipeWorker
from app.workers.voice_worker import WhisperVoiceWorker


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

            print(f"[RabbitMQ Consumer] 📩 Received task '{task_type}' (Request #{payload.get('request_id')})")

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
                print(f"[RabbitMQ Consumer] Warning: Unknown task_type '{task_type}'")

            return success
        except Exception as e:
            print(f"[RabbitMQ Consumer] Error processing task: {e}")
            return False
        finally:
            db.close()

    def start((self)) -> None:
        """Start listening continuously to RabbitMQ task queue."""
        try:
            import pika
        except ImportError:
            print("[RabbitMQ Consumer] Error: 'pika' package not installed. Run: pip install pika")
            return

        credentials = pika.PlainCredentials(self.user, self.password)
        parameters = pika.ConnectionParameters(
            host=self.host,
            port=self.port,
            credentials=credentials,
            heartbeat=600,
            blocked_connection_timeout=300,
        )

        print(f"🚀 Starting RabbitMQ Worker Consumer listening on host '{self.host}:{self.port}', queue '{self.queue_name}'...")

        while True:
            try:
                connection = pika.BlockingConnection(parameters)
                channel = connection.channel()
                channel.queue_declare(queue=self.queue_name, durable=True)
                channel.basic_qos(prefetch_count=1)

                def callback(ch: Any, method: Any, properties: Any, body: bytes) -> None:
                    success = self.process_message(body)
                    if success:
                        ch.basic_ack(delivery_tag=method.delivery_tag)
                    else:
                        # Requeue or nack on failure
                        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

                channel.basic_consume(queue=self.queue_name, on_message_callback=callback)
                print("✅ RabbitMQ Worker Consumer active & waiting for tasks. To exit press CTRL+C")
                channel.start_consuming()

            except KeyboardInterrupt:
                print("\n[RabbitMQ Consumer] Stopping worker gracefully.")
                sys.exit(0)
            except Exception as conn_err:
                print(f"[RabbitMQ Consumer] Connection lost ({conn_err}). Retrying in 5 seconds...")
                time.sleep(5)


if __name__ == "__main__":
    consumer = RabbitMQTaskConsumer()
    consumer.start()
