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

from app.models import Base
from app.services import RequestService


def run_services_test():
    # Setup in-memory SQLite engine
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    db = TestingSessionLocal()
    try:
        service = RequestService(db)

        # 1. Test Text Request Creation
        text_res = service.create_text_request(raw_text_input="chicken breast, garlic, butter, rosemary")
        assert text_res.id is not None
        assert text_res.raw_text_input == "chicken breast, garlic, butter, rosemary"
        print(f"[OK] create_text_request Success! ID: {text_res.id}, Input: '{text_res.raw_text_input}'")

        # 2. Test Image Request Creation
        fake_image_bytes = b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00"  # mock JPEG header bytes
        img_res = service.create_image_request(file_bytes=fake_image_bytes, filename="refrigerator_photo.jpg")
        assert img_res.id is not None
        print(f"[OK] create_image_request Success! ID: {img_res.id}")

        # 3. Test Voice Request Creation
        fake_audio_bytes = b"RIFF....WAVEfmt "  # mock WAV header bytes
        voice_res = service.create_voice_request(file_bytes=fake_audio_bytes, filename="voice_ingredients.wav")
        assert voice_res.id is not None
        print(f"[OK] create_voice_request Success! ID: {voice_res.id}")

        # 4. Test Get Request Details
        details = service.get_request_details(img_res.id)
        assert details is not None
        assert len(details.images) == 1
        print(f"[OK] get_request_details Success! Request #{details.id} has {len(details.images)} images.")

        # 5. Test Recipe Selection
        select_res = service.select_recipe(request_id=text_res.id, recipe_title="Garlic Butter Chicken")
        assert select_res.selected_recipe == {"title": "Garlic Butter Chicken"}
        print(f"[OK] select_recipe Success! Selected: {select_res.selected_recipe}")

        print("\nALL SERVICES LAYER TESTS PASSED SUCCESSFULLY!")

    finally:
        db.close()


if __name__ == "__main__":
    run_services_test()
