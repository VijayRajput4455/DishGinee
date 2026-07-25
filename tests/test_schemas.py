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

from app.enums import InputType, RequestStatus
from app.models import Base
from app.repositories import RequestRepository
from app.schemas import (
    APIResponse,
    CookingGuide,
    CookingGuideStep,
    MacroNutrients,
    RecipeOption,
    RecipeSelectRequest,
    RequestCreateText,
    RequestDetailResponse,
)


def run_schemas_test():
    # 1. Test Input Schema Validation
    text_input = RequestCreateText(raw_text_input="tomato, basil, mozzarella, olive oil")
    print(f"[OK] RequestCreateText Validated: '{text_input.raw_text_input}'")

    select_req = RecipeSelectRequest(recipe_title="Margherita Pizza", recipe_index=0)
    print(f"[OK] RecipeSelectRequest Validated: '{select_req.recipe_title}' (Index: {select_req.recipe_index})")

    # 2. Test CookingGuide & LLM Stage 2 Schemas
    guide = CookingGuide(
        title="Caprese Salad",
        servings=2,
        prep_time="10 mins",
        cook_time="0 mins",
        ingredients=["2 Tomatoes", "100g Mozzarella", "Fresh Basil", "Olive Oil"],
        steps=[
            CookingGuideStep(step_number=1, instruction="Slice tomatoes and mozzarella evenly."),
            CookingGuideStep(step_number=2, instruction="Arrange slices alternately with basil leaves."),
        ],
        macros=MacroNutrients(calories=250, protein_g=12.5, carbs_g=5.0, fats_g=18.0),
    )
    print(f"[OK] CookingGuide Validated: '{guide.title}' with {len(guide.steps)} steps and {guide.macros.calories} kcal.")

    # 3. Test SQLAlchemy ORM -> Pydantic Schema Serialization (from_attributes=True)
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    db = TestingSessionLocal()
    try:
        repo = RequestRepository(db)
        # Create DB record
        req_db = repo.create_request(input_type=InputType.TEXT, raw_text_input="tomato, cheese")
        repo.add_request_image(request_id=req_db.id, original_image="minio://raw/caprese.jpg")
        repo.upsert_request_output(request_id=req_db.id, ingredients=["tomato", "cheese"])

        # Fetch eagerly loaded model
        req_fetched = repo.get_with_details(req_db.id)

        # Convert ORM model to Pydantic DTO
        dto = RequestDetailResponse.model_validate(req_fetched)
        assert dto.id == req_db.id
        assert len(dto.images) == 1
        assert dto.output is not None
        assert dto.output.ingredients == ["tomato", "cheese"]

        print(f"[OK] ORM to Pydantic RequestDetailResponse Conversion Succeeded! (ID: {dto.id}, Images: {len(dto.images)})")

        # 4. Test Generic APIResponse Wrapper
        api_res = APIResponse[RequestDetailResponse](
            success=True,
            message="Request retrieved successfully",
            data=dto,
        )
        assert api_res.data.id == req_db.id
        print(f"[OK] Generic APIResponse[RequestDetailResponse] Wrapped Successfully: success={api_res.success}")

        print("\nALL PYDANTIC V2 SCHEMA TESTS PASSED SUCCESSFULLY!")

    finally:
        db.close()


if __name__ == "__main__":
    run_schemas_test()
