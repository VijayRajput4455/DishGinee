"""End-to-End System Test Script for DishGenie Pipeline.

Simulates complete user journey:
Input Submission -> YOLO Detection -> Ollama 5-Recipe Generation -> Recipe Selection -> Stage 2 Full Cooking Guide
"""

import json
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
from app.workers import CookingGuideWorker, LLMRecipeWorker, YOLOImageWorker


def run_full_system_test():
    print("================================================================")
    print("🧙‍♂️ DISHGENIE END-TO-END SYSTEM TEST")
    print("================================================================\n")

    # Setup in-memory SQLite database
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    db = TestingSessionLocal()
    try:
        service = RequestService(db)
        yolo_worker = YOLOImageWorker()
        recipe_worker = LLMRecipeWorker()
        guide_worker = CookingGuideWorker()

        # -------------------------------------------------------------
        # STEP 1: Client Submits Image Request with Indian Cuisine
        # -------------------------------------------------------------
        print("STEP 1: Submitting Image Upload Request (Cuisine: Indian)...")
        fake_fridge_image = b"\xFF\xD8\xFF\xE0MockFridgeImageBytes"
        req_res = service.create_image_request(
            file_bytes=fake_fridge_image,
            filename="refrigerator_food.jpg",
            cuisine="Indian",
        )
        request_id = req_res.id
        print(f"  └─ Request Created Successfully! ID: #{request_id}, InputType: {req_res.input_type}, Status: {req_res.status}\n")

        # -------------------------------------------------------------
        # STEP 2: YOLO Worker Performs Ingredient Detection
        # -------------------------------------------------------------
        print("STEP 2: Running YOLO Computer Vision Worker...")
        yolo_worker.process_image_task(
            payload={"request_id": request_id, "image_url": "minio://dishgenie-bucket/raw/refrigerator_food.jpg"},
            db=db,
        )
        print("  └─ YOLO Detection completed & annotated image stored!\n")

        # -------------------------------------------------------------
        # STEP 3: Stage 1 Ollama LLM Generates 5 Recipe Candidate Options
        # -------------------------------------------------------------
        print("STEP 3: Running Stage 1 Ollama LLM Worker (5 Recipe Generator)...")
        recipe_worker.process_recipe_task(
            payload={
                "request_id": request_id,
                "ingredients": ["tomato", "potato", "butter"],
                "cuisine": "Indian",
            },
            db=db,
        )

        # Retrieve candidate recipes from database
        details_after_stage1 = service.get_request_details(request_id)
        candidate_recipes = details_after_stage1.output.ingredients

        print(f"  └─ Generated {len(candidate_recipes)} Candidate Recipes:")
        for idx, recipe in enumerate(candidate_recipes, 1):
            print(f"     {idx}. {recipe.get('title')} ({recipe.get('prep_time')})")

        print("\n----------------------------------------------------------------")

        # -------------------------------------------------------------
        # STEP 4: Client Selects Preferred Recipe Option
        # -------------------------------------------------------------
        chosen_recipe_title = candidate_recipes[0]["title"]
        print(f"STEP 4: User selects recipe choice: '{chosen_recipe_title}'...")
        service.select_recipe(request_id=request_id, recipe_title=chosen_recipe_title)
        print("  └─ Recipe selection recorded.\n")

        # -------------------------------------------------------------
        # STEP 5: Stage 2 CookingGuideWorker Generates Complete Recipe Guide
        # -------------------------------------------------------------
        print("STEP 5: Running Stage 2 CookingGuideWorker (Ollama qwen2.5:0.5b)...")
        guide_worker.process_cooking_guide_task(
            payload={
                "request_id": request_id,
                "selected_recipe": chosen_recipe_title,
            },
            db=db,
        )
        print("  └─ Stage 2 Complete Cooking Guide generated!\n")

        # -------------------------------------------------------------
        # STEP 6: Verify Final Complete Payload
        # -------------------------------------------------------------
        final_details = service.get_request_details(request_id)
        final_guide = final_details.output.cooking_guide

        print("================================================================")
        print("🍽️ FINAL GENERATED DISHGENIE COOKING GUIDE payload")
        print("================================================================")
        print(f"Recipe Title : {final_guide.get('title')}")
        print(f"Servings     : {final_guide.get('servings')}")
        print(f"Prep Time    : {final_guide.get('prep_time')} | Cook Time: {final_guide.get('cook_time')}")

        print("\n🛒 Required Ingredients:")
        for ing in final_guide.get("ingredients", []):
            if isinstance(ing, dict):
                print(f"  • {ing.get('quantity', '')} {ing.get('item', '')}")
            else:
                print(f"  • {ing}")

        print("\n👨‍🍳 Step-by-Step Instructions:")
        for step in final_guide.get("steps", []):
            tools = f" (Tools: {', '.join(step.get('equipment'))})" if step.get("equipment") else ""
            print(f"  Step {step.get('step_number')}: {step.get('instruction')} [{step.get('duration_minutes')} mins]{tools}")

        if final_guide.get("macros"):
            m = final_guide["macros"]
            print(f"\n📊 Nutritional Macros: {m.get('calories')} kcal | Protein: {m.get('protein_g')}g | Carbs: {m.get('carbs_g')}g | Fats: {m.get('fats_g')}g")

        print("\n================================================================")
        print("🎉 END-TO-END DISHGENIE SYSTEM TEST COMPLETED SUCCESSFULLY!")
        print("================================================================")

    finally:
        db.close()


if __name__ == "__main__":
    run_full_system_test()
