"""Standalone test script to perform real YOLO object detection inference using pre-trained COCO weights (yolov8n.pt)."""

import os
import sys

# Ensure UTF-8 output encoding for Windows terminals
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

def run_real_yolo_test():
    print("🚀 Initializing Real YOLO Detection Test...")

    try:
        from ultralytics import YOLO
        from PIL import Image
    except ImportError:
        print("Installing required dependencies (ultralytics, pillow)...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "ultralytics", "pillow"])
        from ultralytics import YOLO
        from PIL import Image

    # 1. Load YOLOv8 Nano pre-trained model (auto-downloads 6MB model weights if needed)
    print("📦 Loading YOLOv8 model (yolov8n.pt)...")
    model = YOLO("yolov8n.pt")

    # 2. Define test image source (sample online image containing food/objects)
    image_url = "https://ultralytics.com/images/bus.jpg"
    print(f"📷 Running inference on sample image: {image_url}")

    # 3. Perform Inference
    results = model(image_url)

    # 4. Extract Detected Classes & Confidence Scores
    print("\n🔍 Detections Summary:")
    for r in results:
        for box in r.boxes:
            cls_id = int(box.cls[0])
            label = model.names[cls_id]
            conf = float(box.conf[0])
            print(f"  • Found object: '{label}' with confidence {conf:.2%}")

    # 5. Save Annotated Output Image
    output_filename = "test_yolo_annotated.jpg"
    for r in results:
        im_array = r.plot()  # plot a BGR numpy array of predictions
        im = Image.fromarray(im_array[..., ::-1])  # RGB PIL image
        im.save(output_filename)

    print(f"\n✅ YOLO Detection completed! Annotated image saved to: {os.path.abspath(output_filename)}")


if __name__ == "__main__":
    run_real_yolo_test()
