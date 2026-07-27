import urllib.request
import json
import time

BASE_URL = "http://localhost:8000/api/v1"

# Step 1: POST /requests/text
req_payload = {
    "raw_text_input": "tomatoes, potatoes, garlic, butter, spinach, chicken",
    "cuisine": "Indian",
    "is_vegetarian": False
}

data = json.dumps(req_payload).encode("utf-8")
req = urllib.request.Request(f"{BASE_URL}/requests/text", data=data, headers={"Content-Type": "application/json"}, method="POST")

print("Posting text request to API...")
with urllib.request.urlopen(req) as resp:
    res_json = json.loads(resp.read().decode("utf-8"))
    print("Stage 1 Response:", json.dumps(res_json, indent=2))
    req_id = res_json["data"]["id"]

# Step 2: POST /requests/{id}/select-recipe
select_payload = {
    "recipe_title": "Indian Garlic Butter Tomatoes & Potatoes"
}

data_sel = json.dumps(select_payload).encode("utf-8")
req_sel = urllib.request.Request(f"{BASE_URL}/requests/{req_id}/select-recipe", data=data_sel, headers={"Content-Type": "application/json"}, method="POST")

print(f"\nSelecting recipe 'Indian Garlic Butter Tomatoes & Potatoes' for Request #{req_id}...")
start = time.time()
with urllib.request.urlopen(req_sel) as resp_sel:
    sel_json = json.loads(resp_sel.read().decode("utf-8"))
    elapsed = time.time() - start
    print(f"Stage 2 Response received in {elapsed:.2f}s:")
    print("Success:", sel_json.get("success"))
    guide = sel_json.get("data", {}).get("cooking_guide")
    print("Cooking guide present:", guide is not None)
    if guide:
        print("Title:", guide.get("title"))
        print("Steps count:", len(guide.get("steps", [])))
        print("First step:", guide.get("steps", [])[0] if guide.get("steps") else None)
