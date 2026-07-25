from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+psycopg2://dishgenie_user:dishgenie_password@localhost:5432/dishgenie_db"

    # MinIO Object Storage
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "dishgenie_minioadmin"
    MINIO_SECRET_KEY: str = "dishgenie_miniopassword"
    MINIO_BUCKET_NAME: str = "dishgenie-bucket"
    MINIO_SECURE: bool = False

    # RabbitMQ
    RABBITMQ_HOST: str = "localhost"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "dishgenie_rmq_user"
    RABBITMQ_PASSWORD: str = "dishgenie_rmq_password"
    RABBITMQ_QUEUE_NAME: str = "dishgenie_tasks"
    RABBITMQ_FAILED_QUEUE_NAME: str = "dishgenie_tasks_failed"
    RABBITMQ_MAX_RETRIES: int = 3

    # Worker Execution & Logging Settings
    AUTO_START_WORKER: bool = True
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "logs"
    LOG_FILE: str = "dishgenie.log"

    # Ollama Local LLM Settings
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:0.5b"

    # Cloud LLM Fallback Settings
    OPENAI_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4o-mini"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()