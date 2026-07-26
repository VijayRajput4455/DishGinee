import os
import sys
from unittest.mock import MagicMock, patch

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.enums import InputType, RequestStatus
from app.models import Base
from app.repositories import RequestRepository
from app.services.request_service import RequestService
from app.workers.cooking_guide_worker import CookingGuideWorker


def run_recipe_cache_test():
    print("🚀 Initializing Recipe Cooking Guide DB Cache Test...")

    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    db = TestingSessionLocal()
    try:
        req_repo = RequestRepository(db)
        service = RequestService(db)
        worker = CookingGuideWorker()

        # Step 1: Create initial request and populate DB with Paneer Butter Masala cooking guide
        req1 = req_repo.create_request(
            input_type=InputType.TEXT,
            raw_text_input="Paneer Butter Masala",
        )
        sample_guide = {
            "title": "Paneer Butter Masala",
            "servings": 2,
            "prep_time": "15 mins",
            "cook_time": "20 mins",
            "ingredients": ["250g Paneer", "3 Tomatoes", "2 tbsp Butter"],
            "steps": [
                {
                    "step_number": 1,
                    "instruction": "Puree tomatoes and saute ginger garlic in butter.",
                    "duration_minutes": 5,
                    "equipment": ["Pan"],
                }
            ],
            "macros": {"calories": 420, "protein_g": 16.0, "carbs_g": 18.0, "fats_g": 32.0},
        }
        req_repo.upsert_request_output(
            request_id=req1.id,
            selected_recipe={"title": "Paneer Butter Masala"},
            cooking_guide=sample_guide,
        )
        req_repo.update_status(req1.id, RequestStatus.COMPLETED)
        print(f"[OK] Seeded Request #{req1.id} with 'Paneer Butter Masala' cooking guide.")

        # Step 2: Verify find_existing_cooking_guide works for exact and typo matches
        exact_hit = req_repo.find_existing_cooking_guide("Paneer Butter Masala")
        assert exact_hit is not None
        assert exact_hit["title"] == "Paneer Butter Masala"
        print("[OK] find_existing_cooking_guide exact match SUCCESS!")

        typo_hit = req_repo.find_existing_cooking_guide("panner butter masala")
        assert typo_hit is not None
        assert typo_hit["title"] == "Paneer Butter Masala"
        print("[OK] find_existing_cooking_guide typo match ('panner butter masala') SUCCESS!")

        # Step 3: Test RequestService.select_recipe reuses cached guide without calling LLM
        req2 = req_repo.create_request(
            input_type=InputType.TEXT,
            raw_text_input="paneer, butter",
        )
        with patch.object(worker, "generate_full_cooking_guide") as mock_llm_call:
            res = service.select_recipe(request_id=req2.id, recipe_title="panner butter masala")
            mock_llm_call.assert_not_called()
            assert res.cooking_guide is not None
            assert res.cooking_guide["title"] == "Paneer Butter Masala"
            print(f"[OK] RequestService.select_recipe re-used cached guide for Request #{req2.id}! Skipped LLM call.")

        # Step 4: Test CookingGuideWorker.process_cooking_guide_task reuses cached guide
        req3 = req_repo.create_request(
            input_type=InputType.TEXT,
            raw_text_input="paneer, tomato",
        )
        with patch.object(worker, "generate_full_cooking_guide") as mock_worker_llm:
            success = worker.process_cooking_guide_task(
                payload={"request_id": req3.id, "selected_recipe": "Paneer Butter Masala"},
                db=db,
            )
            assert success is True
            mock_worker_llm.assert_not_called()
            output3 = req_repo.get_with_details(req3.id).output
            assert output3.cooking_guide["title"] == "Paneer Butter Masala"
            print(f"[OK] CookingGuideWorker.process_cooking_guide_task re-used cached guide for Request #{req3.id}! Skipped LLM call.")

        print("\n🎉 ALL RECIPE COOKING GUIDE DB CACHE TESTS PASSED SUCCESSFULLY!")

    finally:
        db.close()


if __name__ == "__main__":
    run_recipe_cache_test()
