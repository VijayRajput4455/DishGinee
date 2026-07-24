"""Real YOLO Food & Ingredient Object Detection Inference Test."""

import os
import sys

# Ensure UTF-8 output encoding for Windows terminals
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from PIL import Image
from ultralytics import YOLO


def run_yolo_food_test():
    print("🚀 Initializing Real YOLO Food Detection Test...")

    # 1. Load YOLOv8 Model
    model = YOLO("yolov8n.pt")

    # 2. Food sample image URL (containing fruits/food items)
    food_image_url = "https://raw.githubusercontent.com/ultralytics/ultralytics/main/ultralytics/assets/bus.jpg"

    print("🔍 Running YOLO Inference...")
    results = model("https://images.unsplash.com/photo-1540420773420-3366772f4999?w=800")  # Fresh salad & food ingredients photo

    print("\n🥗 Detected Ingredients / Food Items:")
    food_items = []
    for r in results:
        for box in r.boxes:
            cls_id = int(box.cls[0])
            label = model.names[cls_id]
            conf = float(box.conf[0])
            food_items.append({"label": label, "confidence": conf})
            print(f"  • Detected: '{label}' (Confidence: {conf:.2%})")

    # Save annotated bounding box image
    output_filename = "test_food_annotated.jpg"
    for r in results:
        im_array = r.plot()  # plot BGR numpy array
        im = Image.fromarray(im_array[..., ::-1])  # RGB PIL Image
        im.save(output_filename)

    print(f"\n🎉 Food Detection Test Finished! Annotated image saved to: {os.path.abspath(output_filename)}")


if __name__ == "__main__":
    run_yolo_food_test()
