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
from app.repositories import RequestRepository
from app.workers import LLMRecipeWorker, WhisperVoiceWorker, YOLOImageWorker


def run_workers_test():
    # Setup in-memory SQLite engine
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    db = TestingSessionLocal()
    try:
        req_repo = RequestRepository(db)
        yolo_worker = YOLOImageWorker()
        whisper_worker = WhisperVoiceWorker()
        llm_worker = LLMRecipeWorker()

        # 1. Test YOLO Image Worker Processing
        req_img = req_repo.create_request(input_type=InputType.IMAGE)
        req_repo.add_request_image(request_id=req_img.id, original_image="minio://dishgenie-bucket/raw/test_fridge.jpg")

        yolo_success = yolo_worker.process_image_task(
            payload={"request_id": req_img.id, "image_url": "minio://dishgenie-bucket/raw/test_fridge.jpg"},
            db=db,
        )
        assert yolo_success is True
        print("[OK] YOLOImageWorker successfully processed image task and created annotations!")

        # 2. Test Whisper Voice Worker Processing
        req_voice = req_repo.create_request(input_type=InputType.VOICE, audio_url="minio://dishgenie-bucket/audio/test_rec.wav")
        voice_success = whisper_worker.process_voice_task(
            payload={"request_id": req_voice.id, "audio_url": "minio://dishgenie-bucket/audio/test_rec.wav"},
            db=db,
        )
        assert voice_success is True
        print("[OK] WhisperVoiceWorker successfully processed voice task and transcribed audio!")

        # 3. Test LLM Stage 1 Recipe Options Generation
        recipe_success = llm_worker.process_recipe_task(
            payload={"request_id": req_img.id, "ingredients": ["tomato", "bell pepper", "onion"]},
            db=db,
        )
        assert recipe_success is True
        print("[OK] LLMRecipeWorker successfully generated Stage 1 recipe candidate options!")

        # 4. Test LLM Stage 2 Cooking Guide Generation
        guide_success = llm_worker.process_guide_task(
            payload={"request_id": req_img.id, "selected_recipe": "Garlic Butter Tomato Delight"},
            db=db,
        )
        assert guide_success is True
        print("[OK] LLMRecipeWorker successfully generated Stage 2 detailed cooking guide!")

        print("\nALL WORKER PIPELINE TESTS PASSED SUCCESSFULLY!")

    finally:
        db.close()


if __name__ == "__main__":
    run_workers_test()
