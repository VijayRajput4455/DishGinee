from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enums import ImageStatus
from app.models.request_image import RequestImage
from app.repositories.base_repository import BaseRepository


class RequestImageRepository(BaseRepository[RequestImage]):
    """Repository for managing RequestImage database operations."""

    def __init__(self, db: Session) -> None:
        super().__init__(RequestImage, db)

    def add_image(
        self,
        request_id: int,
        original_image: str,
        status: ImageStatus = ImageStatus.UPLOADED,
    ) -> RequestImage:
        """Create and persist a new image record linked to a request."""
        image_obj = RequestImage(
            request_id=request_id,
            original_image=original_image,
            status=status,
        )
        return self.create(image_obj)

    def update_image_status(
        self,
        image_id: int,
        status: ImageStatus,
        annotated_image: str | None = None,
    ) -> RequestImage | None:
        """Update processing status and optional annotated image storage path."""
        image_obj = self.get_by_id(image_id)
        if image_obj is None:
            return None

        image_obj.status = status
        if annotated_image is not None:
            image_obj.annotated_image = annotated_image

        return self.update(image_obj)

    def get_images_by_request_id(self, request_id: int) -> list[RequestImage]:
        """Fetch all image records for a given request."""
        stmt = select(RequestImage).where(RequestImage.request_id == request_id)
        return list(self.db.execute(stmt).scalars().all())
