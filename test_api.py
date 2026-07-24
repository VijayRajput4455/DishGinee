"""Unit test script to verify FastAPI endpoints using TestClient."""

import sys
from io import BytesIO

# Ensure UTF-8 output encoding for Windows terminals
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import get_db
from app.main import app
from app.models import Base

# Setup in-memory SQLite engine for API testing
engine = create_engine("sqlite:///:memory:", echo=False)
Base.metadata.create_all(bind=engine)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def run_api_test():
    # 1. Test Health Endpoint
    res_health = client.get("/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "healthy"
    print("[OK] GET /health returned 200 OK")

    # 2. Test Text Request Endpoint
    res_text = client.post(
        "/api/v1/requests/text",
        json={"raw_text_input": "tomatoes, garlic, olive oil, pasta"},
    )
    assert res_text.status_code == 201
    text_data = res_text.json()
    assert text_data["success"] is True
    req_id = text_data["data"]["id"]
    print(f"[OK] POST /api/v1/requests/text returned 201 Created (ID: {req_id})")

    # 3. Test Image Upload Endpoint
    fake_image = BytesIO(b"\xFF\xD8\xFF\xE0MockImageBytes")
    res_img = client.post(
        "/api/v1/requests/image",
        files={"file": ("fridge.jpg", fake_image, "image/jpeg")},
    )
    assert res_img.status_code == 201
    img_data = res_img.json()
    img_req_id = img_data["data"]["id"]
    print(f"[OK] POST /api/v1/requests/image returned 201 Created (ID: {img_req_id})")

    # 4. Test Voice Upload Endpoint
    fake_audio = BytesIO(b"RIFF....WAVEfmt MockAudioBytes")
    res_voice = client.post(
        "/api/v1/requests/voice",
        files={"file": ("voice.wav", fake_audio, "audio/wav")},
    )
    assert res_voice.status_code == 201
    print(f"[OK] POST /api/v1/requests/voice returned 201 Created")

    # 5. Test Get Request Details Endpoint
    res_details = client.get(f"/api/v1/requests/{img_req_id}")
    assert res_details.status_code == 200
    details_data = res_details.json()
    assert details_data["data"]["id"] == img_req_id
    assert len(details_data["data"]["images"]) == 1
    print(f"[OK] GET /api/v1/requests/{img_req_id} returned 200 OK with nested images")

    # 6. Test Select Recipe Endpoint
    res_select = client.post(
        f"/api/v1/requests/{req_id}/select-recipe",
        json={"recipe_title": "Garlic Tomato Pasta"},
    )
    assert res_select.status_code == 200
    select_data = res_select.json()
    assert select_data["data"]["selected_recipe"] == {"title": "Garlic Tomato Pasta"}
    print(f"[OK] POST /api/v1/requests/{req_id}/select-recipe returned 200 OK")

    print("\nALL FASTAPI ROUTE TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    run_api_test()
