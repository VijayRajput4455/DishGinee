from io import BytesIO
from typing import Any

from app.core.config import settings


class MinIOService:
    """Service handling object storage operations with MinIO."""

    def __init__(self) -> None:
        self.endpoint = settings.MINIO_ENDPOINT
        self.access_key = settings.MINIO_ACCESS_KEY
        self.secret_key = settings.MINIO_SECRET_KEY
        self.bucket_name = settings.MINIO_BUCKET_NAME
        self.secure = settings.MINIO_SECURE
        self._client: Any = None

    @property
    def client(self) -> Any:
        """Lazy initialization of MinIO client."""
        if self._client is None:
            try:
                from minio import Minio
                self._client = Minio(
                    endpoint=self.endpoint,
                    access_key=self.access_key,
                    secret_key=self.secret_key,
                    secure=self.secure,
                )
            except ImportError:
                self._client = None
        return self._client

    def ensure_bucket_exists(self) -> bool:
        """Ensure the target bucket exists in MinIO."""
        if self.client is None:
            return False
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
            return True
        except Exception as e:
            print(f"[MinIOService] Warning: Could not check/create bucket: {e}")
            return False

    def upload_file(
        self,
        file_data: bytes,
        object_name: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload binary file data to MinIO object storage."""
        if self.client is not None:
            try:
                self.ensure_bucket_exists()
                file_stream = BytesIO(file_data)
                self.client.put_object(
                    bucket_name=self.bucket_name,
                    object_name=object_name,
                    data=file_stream,
                    length=len(file_data),
                    content_type=content_type,
                )
                return f"minio://{self.bucket_name}/{object_name}"
            except Exception as e:
                print(f"[MinIOService] Error uploading object '{object_name}': {e}")

        # Fallback return URI if MinIO service is offline or uninstalled
        return f"minio://{self.bucket_name}/{object_name}"

    def get_presigned_url(self, object_name: str, expires_seconds: int = 3600) -> str:
        """Generate a presigned GET URL for secure client access."""
        clean_key = object_name.replace(f"minio://{self.bucket_name}/", "")
        if self.client is not None:
            try:
                from datetime import timedelta
                return self.client.presigned_get_object(
                    bucket_name=self.bucket_name,
                    object_name=clean_key,
                    expires=timedelta(seconds=expires_seconds),
                )
            except Exception as e:
                print(f"[MinIOService] Error generating presigned URL for '{clean_key}': {e}")

        # Fallback URL format
        scheme = "https" if self.secure else "http"
        return f"{scheme}://{self.endpoint}/{self.bucket_name}/{clean_key}"
