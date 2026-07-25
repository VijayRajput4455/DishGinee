import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Ensure UTF-8 output encoding for Windows terminals
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.enums import ImageStatus, InputType, RequestStatus
from app.models import Base
from app.repositories import (
    RequestImageRepository,
    RequestOutputRepository,
    RequestRepository,
)


def run_repository_test():
    # 1. Setup in-memory SQLite engine for fast verification
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    db = TestingSessionLocal()
    try:
        req_repo = RequestRepository(db)
        img_repo = RequestImageRepository(db)
        out_repo = RequestOutputRepository(db)

        # 2. Test RequestRepository
        req_img = req_repo.create_request(input_type=InputType.IMAGE)
        print(f"[OK] Created Request ID: {req_img.id}, Status: {req_img.status}")

        # 3. Test RequestImageRepository
        img_rec = img_repo.add_image(
            request_id=req_img.id,
            original_image="minio://dishgenie-images/raw/photo_123.jpg",
        )
        print(f"[OK] Added Image via RequestImageRepository ID: {img_rec.id}")

        updated_img = img_repo.update_image_status(
            image_id=img_rec.id,
            status=ImageStatus.PROCESSED,
            annotated_image="minio://dishgenie-images/annotated/photo_123_boxes.jpg",
        )
        print(f"[OK] Updated Image Status: {updated_img.status}")

        # 4. Test RequestOutputRepository
        output_rec = out_repo.upsert_output(
            request_id=req_img.id,
            ingredients=["tomato", "onion", "garlic", "chicken breast"],
        )
        print(f"[OK] Upserted Output via RequestOutputRepository: {output_rec.ingredients}")

        # 5. Test Get With Details
        fetched_req = req_repo.get_with_details(req_img.id)
        assert fetched_req is not None
        assert len(fetched_req.images) == 1
        assert fetched_req.output is not None
        assert fetched_req.output.ingredients == ["tomato", "onion", "garlic", "chicken breast"]

        print(f"[OK] Joined eager load verified for Request #{fetched_req.id}")
        print("\nALL REPOSITORY LAYER TESTS PASSED SUCCESSFULLY!")

    finally:
        db.close()


if __name__ == "__main__":
    run_repository_test()
