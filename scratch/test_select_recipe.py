import sys
import os
sys.path.insert(0, os.getcwd())

from app.core.database import SessionLocal
from app.services.request_service import RequestService

db = SessionLocal()
service = RequestService(db)

# 1. Create a request
req = service.create_text_request("tomatoes, potatoes, garlic, butter")
print(f"Created Request #{req.id}")

# 2. Select recipe
try:
    res = service.select_recipe(req.id, "Indian Garlic Butter Tomatoes & Potatoes")
    print("select_recipe return type:", type(res))
    print("cooking_guide in res:", res.cooking_guide is not None)
    if res.cooking_guide:
        print("Title:", res.cooking_guide.get("title"))
        print("Steps count:", len(res.cooking_guide.get("steps", [])))
except Exception as e:
    print("ERROR in select_recipe:", e)
    import traceback
    traceback.print_exc()
finally:
    db.close()
