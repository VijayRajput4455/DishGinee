"""Launcher script for DishGenie RabbitMQ Background Worker Consumer."""

import sys

# Ensure UTF-8 output encoding for Windows terminals
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from app.workers.consumer import RabbitMQTaskConsumer

if __name__ == "__main__":
    consumer = RabbitMQTaskConsumer()
    consumer.start()
