# YOLO Model Weights Storage

This directory stores local PyTorch/YOLO computer vision model weights used by `YOLOImageWorker` for ingredient detection.

## Recommended Weights Files:
- `yolo26m.pt`: Default YOLO model weights (YOLO26 Medium).
- `yolo_food.pt` / `yolo_ingredients.pt`: Custom fine-tuned food dataset detection model.

Binary `.pt` files are ignored by git via `.gitignore` to keep repository size compact.
