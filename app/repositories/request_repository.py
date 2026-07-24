from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.enums import ImageStatus, InputType, RequestStatus
from app.models import Request, RequestImage, RequestOutput
from app.repositories.base_repository import BaseRepository


class RequestRepository(BaseRepository[Request]):
    """Domain-specific repository for managing Requests, RequestImages, and RequestOutputs."""

    def __init__(self, db: Session) -> None:
        super().__init__(Request, db)

    def get_with_details(self, request_id: int) -> Request | None:
        """Fetch a Request with its associated RequestImages and RequestOutput eagerly loaded."""
        stmt = (
            select(Request)
            .options(
                joinedload(Request.images),
                joinedload(Request.output),
            )
            .where(Request.id == request_id)
        )
        return self.db.execute(stmt).unique().scalar_one_or_none()

    def create_request(
        self,
        input_type: InputType,
        raw_text_input: str | None = None,
        audio_url: str | None = None,
        cuisine: str | None = None,
    ) -> Request:
        """Create and persist a new user request with optional cuisine preference."""
        request_obj = Request(
            input_type=input_type,
            status=RequestStatus.PENDING,
            raw_text_input=raw_text_input,
            audio_url=audio_url,
            cuisine=cuisine,
        )
        return self.create(request_obj)

    def update_status(self, request_id: int, status: RequestStatus) -> Request | None:
        """Update the workflow execution status of a request."""
        request_obj = self.get_by_id(request_id)
        if request_obj is None:
            return None

        request_obj.status = status
        self.db.add(request_obj)
        self.db.commit()
        self.db.refresh(request_obj)
        return request_obj

    def add_request_image(
        self,
        request_id: int,
        original_image: str,
        status: ImageStatus = ImageStatus.UPLOADED,
    ) -> RequestImage:
        """Associate a new uploaded image record with a request."""
        image_obj = RequestImage(
            request_id=request_id,
            original_image=original_image,
            status=status,
        )
        self.db.add(image_obj)
        self.db.commit()
        self.db.refresh(image_obj)
        return image_obj

    def update_image_status(
        self,
        image_id: int,
        status: ImageStatus,
        annotated_image: str | None = None,
    ) -> RequestImage | None:
        """Update an image record's processing status and annotated image storage key."""
        stmt = select(RequestImage).where(RequestImage.id == image_id)
        image_obj = self.db.execute(stmt).scalar_one_or_none()
        if image_obj is None:
            return None

        image_obj.status = status
        if annotated_image is not None:
            image_obj.annotated_image = annotated_image

        self.db.add(image_obj)
        self.db.commit()
        self.db.refresh(image_obj)
        return image_obj

    def upsert_request_output(
        self,
        request_id: int,
        ingredients: dict[str, Any] | list[Any] | None = None,
        selected_recipe: dict[str, Any] | None = None,
        cooking_guide: dict[str, Any] | None = None,
    ) -> RequestOutput:
        """Create or update the RequestOutput payload for a given request_id."""
        stmt = select(RequestOutput).where(RequestOutput.request_id == request_id)
        output_obj = self.db.execute(stmt).scalar_one_or_none()

        if output_obj is None:
            output_obj = RequestOutput(
                request_id=request_id,
                ingredients=ingredients,
                selected_recipe=selected_recipe,
                cooking_guide=cooking_guide,
            )
        else:
            if ingredients is not None:
                output_obj.ingredients = ingredients
            if selected_recipe is not None:
                output_obj.selected_recipe = selected_recipe
            if cooking_guide is not None:
                output_obj.cooking_guide = cooking_guide

        self.db.add(output_obj)
        self.db.commit()
        self.db.refresh(output_obj)
        return output_obj
