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
        """Ensure the target bucket exists in MinIO and has public read policy."""
        if self.client is None:
            return False
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)

            import json
            policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"AWS": ["*"]},
                        "Action": ["s3:GetObject"],
                        "Resource": [f"arn:aws:s3:::{self.bucket_name}/*"]
                    }
                ]
            }
            self.client.set_bucket_policy(self.bucket_name, json.dumps(policy))
            return True
        except Exception as e:
            print(f"[MinIOService] Warning: Could not check/set bucket policy: {e}")
            return True

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

    def download_file(self, object_name: str) -> bytes | None:
        """Download binary object data from MinIO object storage."""
        clean_key = object_name.replace(f"minio://{self.bucket_name}/", "")
        if self.client is not None:
            try:
                response = self.client.get_object(self.bucket_name, clean_key)
                data = response.read()
                response.close()
                response.release_conn()
                return data
            except Exception as e:
                print(f"[MinIOService] Error downloading object '{clean_key}': {e}")
        return None

    def download_file_by_url(self, url: str) -> bytes | None:
        """Extract object key from storage URL or minio URI and download file bytes."""
        if not url:
            return None
        clean_key = (
            url.replace(f"minio://{self.bucket_name}/", "")
            .replace(f"http://minio:9000/{self.bucket_name}/", "")
            .replace(f"http://localhost:9000/{self.bucket_name}/", "")
            .replace(f"http://127.0.0.1:9000/{self.bucket_name}/", "")
            .replace("minio://", "")
            .replace(f"{self.bucket_name}/", "")
            .lstrip("/")
        )
        if "?" in clean_key:
            clean_key = clean_key.split("?")[0]
        return self.download_file(clean_key)

    def get_presigned_url(self, object_name: str, expires_seconds: int = 3600) -> str:
        """Generate client access URL for MinIO storage objects.
        
        Because dishgenie-bucket has a public read policy enabled, clean public URLs
        without presigned query signatures are used to avoid SignatureDoesNotMatch errors
        when switching between Docker internal network (minio:9000) and client host (localhost:9000).
        """
        if not object_name:
            return ""

        # Handle already formatted HTTP/HTTPS URLs
        if object_name.startswith("http://") or object_name.startswith("https://"):
            url = object_name.replace("minio:9000", "localhost:9000")
            if "X-Amz-Signature" in url and ("localhost:9000" in url or "127.0.0.1:9000" in url):
                url = url.split("?")[0]
            return url

        clean_key = (
            object_name.replace(f"minio://{self.bucket_name}/", "")
            .replace("minio://", "")
            .replace(f"{self.bucket_name}/", "")
            .lstrip("/")
        )

        scheme = "https" if self.secure else "http"
        public_endpoint = self.endpoint.replace("minio:9000", "localhost:9000")
        return f"{scheme}://{public_endpoint}/{self.bucket_name}/{clean_key}"
