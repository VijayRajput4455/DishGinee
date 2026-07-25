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
from app.workers import LLMRecipeWorker


def run_ollama_test():
    print("🚀 Initializing Ollama 5-Recipe & Cuisine Generation Test...")

    # Setup in-memory SQLite engine
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    db = TestingSessionLocal()
    try:
        req_repo = RequestRepository(db)
        worker = LLMRecipeWorker()

        # Test case ingredients & cuisine
        ingredients = ["tomato", "potato", "butter"]
        cuisine = "Indian"

        # 1. Create Request record in DB with cuisine
        req_obj = req_repo.create_request(
            input_type=InputType.TEXT,
            raw_text_input="tomato, potato, butter",
            cuisine=cuisine,
        )
        print(f"[OK] Created Request ID: {req_obj.id}, Cuisine: '{req_obj.cuisine}'")

        # 2. Execute process_recipe_task (Ollama 5-recipe generator)
        success = worker.process_recipe_task(
            payload={
                "request_id": req_obj.id,
                "ingredients": ingredients,
                "cuisine": cuisine,
            },
            db=db,
        )
        assert success is True

        # 3. Retrieve generated output from DB
        output = req_repo.get_with_details(req_obj.id).output
        assert output is not None
        recipes = output.ingredients  # Stores list of 5 candidate recipes
        assert len(recipes) == 5, f"Expected 5 recipes, got {len(recipes)}"

        print(f"\n🎉 Successfully Generated {len(recipes)} Distinct Recipes (Cuisine: {cuisine}):")
        for idx, r in enumerate(recipes, 1):
            print(f"  {idx}. {r.get('title')} ({r.get('prep_time')})")
            print(f"     - Description: {r.get('description')}")
            print(f"     - Missing Ingredients: {', '.join(r.get('missing_ingredients', []))}\n")

        # 4. Test Stage 2 Detailed Cooking Guide Generation
        first_recipe_title = recipes[0]["title"]
        guide_success = worker.process_guide_task(
            payload={
                "request_id": req_obj.id,
                "selected_recipe": first_recipe_title,
            },
            db=db,
        )
        assert guide_success is True

        # Fetch updated output guide
        updated_output = req_repo.get_with_details(req_obj.id).output
        guide = updated_output.cooking_guide
        assert guide["title"] == first_recipe_title
        assert len(guide["steps"]) > 0

        print(f"✅ Stage 2 Cooking Guide Verified for '{guide['title']}' with {len(guide['steps'])} detailed steps!")
        print("\nALL OLLAMA 5-RECIPE & CUISINE TESTS PASSED SUCCESSFULLY!")

    finally:
        db.close()


if __name__ == "__main__":
    run_ollama_test()
