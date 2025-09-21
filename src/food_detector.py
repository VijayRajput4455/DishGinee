import os
from ultralytics import YOLO
from app.logger import get_logger  # ✅ import our custom logger

logger = get_logger(__name__)

class FoodDetector:
    def __init__(self, model_path: str = "models/Veg_best.pt"):
        """
        Initialize YOLO model.
        Loads a custom model if available, otherwise raises error.
        """
        abs_model_path = os.path.abspath(model_path)

        if not os.path.exists(abs_model_path):
            logger.error(f"❌ Model file not found at: {abs_model_path}")
            raise FileNotFoundError(f"YOLO model not found at {abs_model_path}")

        # Load YOLO model
        self.model = YOLO(abs_model_path)
        logger.info(f"✅ Loaded YOLO model from: {abs_model_path}")
        logger.debug(f"Model classes: {self.model.names}")

    def detect_food(self, image_path: str, conf_threshold: float = 0.5):
        """
        Detect objects in a single image and return list of detected food items.
        """
        if not os.path.exists(image_path):
            logger.error(f"❌ Image not found: {image_path}")
            raise FileNotFoundError(f"Image not found: {image_path}")

        if self.model is None:
            raise RuntimeError("❌ YOLO model not loaded properly.")

        logger.info(f"🔍 Detecting food in: {image_path}")
        results = self.model.predict(image_path, conf=conf_threshold)
        detected_items = []

        for result in results:
            for box in result.boxes:
                label = self.model.names[int(box.cls)]
                conf = float(box.conf)
                if conf >= conf_threshold:
                    detected_items.append(label)

        logger.info(f"✅ Detected {len(detected_items)} items in {os.path.basename(image_path)}")
        logger.debug(f"Detections: {detected_items}")
        return detected_items

    def detect_multiple(self, image_paths: list, conf_threshold: float = 0.5):
        """
        Detect objects in multiple images.
        Returns a dict: {image_path: [labels...]}
        """
        if self.model is None:
            raise RuntimeError("❌ YOLO model not loaded properly.")

        logger.info(f"📂 Running detection on {len(image_paths)} images...")
        all_detections = []

        for path in image_paths:
            if not os.path.exists(path):
                logger.warning(f"⚠️ Skipping missing image: {path}")
                continue

            detections = self.detect_food(path, conf_threshold=conf_threshold)
            all_detections.append(detections)

        logger.info("✅ Finished multi-image detection")
        logger.debug(f"All detections: {all_detections}")
        return all_detections
