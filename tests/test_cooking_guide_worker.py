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

from app.enums import InputType
from app.models import Base
from app.repositories import RequestRepository
from app.workers import CookingGuideWorker


def run_cooking_guide_worker_test():
    print("🚀 Initializing CookingGuideWorker Stage 2 Test...")

    # Setup in-memory SQLite engine
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    db = TestingSessionLocal()
    try:
        req_repo = RequestRepository(db)
        worker = CookingGuideWorker()

        # 1. Create Request record in DB
        selected_recipe_title = "Indian Garlic Butter Tomato & Potato"
        req_obj = req_repo.create_request(
            input_type=InputType.TEXT,
            raw_text_input="tomato, potato, butter",
            cuisine="Indian",
        )
        print(f"[OK] Created Request ID: {req_obj.id} for recipe: '{selected_recipe_title}'")

        # 2. Execute process_cooking_guide_task
        success = worker.process_cooking_guide_task(
            payload={
                "request_id": req_obj.id,
                "selected_recipe": selected_recipe_title,
            },
            db=db,
        )
        assert success is True

        # 3. Retrieve generated full cooking guide from DB
        output = req_repo.get_with_details(req_obj.id).output
        assert output is not None
        guide = output.cooking_guide
        assert guide is not None
        assert guide["title"] == selected_recipe_title
        assert len(guide["steps"]) > 0

        print(f"\n🎉 Successfully Generated Complete Cooking Guide for '{guide['title']}':")
        print(f"  • Servings: {guide.get('servings')} | Prep Time: {guide.get('prep_time')} | Cook Time: {guide.get('cook_time')}")
        print(f"  • Ingredients List ({len(guide.get('ingredients', []))} items):")
        for ing in guide.get("ingredients", []):
            print(f"    - {ing}")

        print(f"\n  • Step-by-Step Instructions ({len(guide.get('steps', []))} steps):")
        for step in guide.get("steps", []):
            eq_str = f" [Tools: {', '.join(step.get('equipment', []))}]" if step.get("equipment") else ""
            print(f"    Step {step.get('step_number')}: {step.get('instruction')} ({step.get('duration_minutes')} mins){eq_str}")

        if guide.get("macros"):
            m = guide["macros"]
            print(f"\n  • Nutritional Information (per serving): {m.get('calories')} kcal | Protein: {m.get('protein_g')}g | Carbs: {m.get('carbs_g')}g | Fats: {m.get('fats_g')}g")

        if guide.get("substitutions"):
            print(f"\n  • Substitutions: {', '.join(guide.get('substitutions'))}")

        print("\nALL STAGE 2 COOKING GUIDE WORKER TESTS PASSED SUCCESSFULLY!")

    finally:
        db.close()


if __name__ == "__main__":
    run_cooking_guide_worker_test()
