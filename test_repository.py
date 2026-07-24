"""Unit test script to verify RequestRepository data access layer methods."""

import sys

# Ensure UTF-8 output encoding for Windows terminals
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.enums import ImageStatus, InputType, RequestStatus
from app.models import Base
from app.repositories import RequestRepository


def run_repository_test():
    # 1. Setup in-memory SQLite engine for fast verification
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    db = TestingSessionLocal()
    try:
        repo = RequestRepository(db)

        # 2. Test Create Request (IMAGE)
        req_img = repo.create_request(input_type=InputType.IMAGE)
        print(f"[OK] Created Request ID: {req_img.id}, Status: {req_img.status}")

        # 3. Test Add Request Image
        img_rec = repo.add_request_image(
            request_id=req_img.id,
            original_image="minio://dishgenie-images/raw/photo_123.jpg",
        )
        print(f"[OK] Added Image Record ID: {img_rec.id}, Image Path: {img_rec.original_image}")

        # 4. Test Update Image Status
        updated_img = repo.update_image_status(
            image_id=img_rec.id,
            status=ImageStatus.PROCESSED,
            annotated_image="minio://dishgenie-images/annotated/photo_123_boxes.jpg",
        )
        print(f"[OK] Updated Image Status: {updated_img.status}, Annotated: {updated_img.annotated_image}")

        # 5. Test Upsert Request Output (Detected Ingredients)
        output_rec = repo.upsert_request_output(
            request_id=req_img.id,
            ingredients=["tomato", "onion", "garlic", "chicken breast"],
        )
        print(f"[OK] Upserted Output Ingredients: {output_rec.ingredients}")

        # 6. Test Update Request Status
        req_updated = repo.update_status(request_id=req_img.id, status=RequestStatus.COMPLETED)
        print(f"[OK] Updated Request Status: {req_updated.status}")

        # 7. Test Get With Details (Joined Eager Load)
        fetched_req = repo.get_with_details(req_img.id)
        assert fetched_req is not None
        assert len(fetched_req.images) == 1
        assert fetched_req.output is not None
        assert fetched_req.output.ingredients == ["tomato", "onion", "garlic", "chicken breast"]

        print(f"[OK] get_with_details Success! Request #{fetched_req.id} has {len(fetched_req.images)} images and output attached.")

        # 8. Test Text and Voice Request Creation
        text_req = repo.create_request(input_type=InputType.TEXT, raw_text_input="eggs, milk, flour, butter")
        print(f"[OK] Created Text Request ID: {text_req.id}, Text: '{text_req.raw_text_input}'")

        voice_req = repo.create_request(input_type=InputType.VOICE, audio_url="minio://dishgenie-audio/rec_99.wav")
        print(f"[OK] Created Voice Request ID: {voice_req.id}, Audio URL: '{voice_req.audio_url}'")

        print("\nALL REPOSITORY LAYER TESTS PASSED SUCCESSFULLY!")

    finally:
        db.close()


if __name__ == "__main__":
    run_repository_test()
