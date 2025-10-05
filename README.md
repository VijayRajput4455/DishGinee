# 🍽️ Dishginee

**Dishginee** is an **AI-powered food recognition and recipe recommendation system** that detects food items from images and generates **personalized recipes** with step-by-step instructions, nutrition insights, and tips to enhance your dishes.

> 🍳 Make cooking smarter, faster, and fun with AI!

---

## 📑 Table of Contents

1. [Overview](#-overview)
2. [Key Features](#-key-features)
3. [Tech Stack](#-tech-stack)
4. [System Workflow](#-system-workflow)
5. [Project Structure](#-project-structure)
6. [Requirements](#-requirements)
7. [Getting Started](#-getting-started)
8. [Sample Workflow](#-sample-workflow)
9. [Future Enhancements](#-future-enhancements)

---

## 🧠 Overview

**Dishginee** integrates **YOLOv8** for real-time food detection with **Large Language Models (LLMs)** for generating recipes and cooking instructions.
It helps users discover delicious dishes and provides **nutrition insights** and **suggestions** for improving meals.

---

## 🔑 Key Features

| Feature                               | Description                                                                           |
| ------------------------------------- | ------------------------------------------------------------------------------------- |
| **Image-Based Food Recognition**      | Detects food items in single or multiple images using **YOLOv8**.                     |
| **Personalized Recipe Suggestions**   | Generates **5 recipe suggestions** based on detected items and preferred cuisine.     |
| **Step-by-Step Cooking Instructions** | Provides detailed preparation steps.                                                  |
| **Nutrition Insights**                | Displays calories, macronutrients, and optional ingredient suggestions.               |
| **User-Friendly Experience**          | Smooth integration of computer vision and language models for an intuitive interface. |

---

## 🛠️ Tech Stack

| Layer               | Technology                                                 |
| ------------------- | ---------------------------------------------------------- |
| **Computer Vision** | YOLOv8 (real-time detection)                               |
| **NLP / LLM**       | Large Language Models for recipe generation & instructions |
| **Backend**         | Python, FastAPI                                            |
| **Environment**     | Conda, Python 3.10                                         |
| **Dependencies**    | OpenCV, PyTorch, Transformers, Uvicorn                     |

---

## ⚙️ System Workflow

1. **Upload Images** – Users upload one or more images of food.
2. **Food Detection** – YOLOv8 detects all food items.
3. **Recipe Prediction** – LLM generates **5 personalized recipe suggestions**.
4. **Recipe Selection** – User selects a recipe.
5. **Cooking Instructions** – Step-by-step instructions are displayed.
6. **Nutrition & Recommendations** – Nutrition info and optional ingredient suggestions are provided.

---

## 📁 Project Structure

```
Dishginee/
│
├── app/
│   ├── endpoints/               # API endpoint implementations
│   ├── logger.py                # Custom logging configuration
│   └── main.py                  # Entry point for running the app
│
├── assets/
│   └── Food.jpeg                # Sample food image
│
├── images/                      # Directory for input food images
│
├── logs/
│   └── dishginee.log            # Log file for tracking events and errors
│
├── models/
│   └── Veg_best.pt              # YOLO model or trained weights
│
├── src/
│   ├── food_detector.py         # Handles food detection using YOLO
│   ├── recipe_details_generator.py # Generates detailed recipe steps
│   └── recipe_names_generator.py   # Suggests recipe names from detected items
│
├── requirements.txt             # Python dependencies
└── README.md                    # Project documentation
```

---

## 📦 Requirements

**Python Packages**:

```text
# FastAPI - Web framework for building APIs
fastapi== 0.117.1

# Uvicorn - ASGI server to run FastAPI applications
uvicorn==0.36.0

# Ultralytics - YOLO object detection and computer vision tasks
ultralytics==8.3.202

# python-multipart - For handling file uploads in FastAPI
python-multipart==0.0.20
```

**Hardware / Software Requirements**:

* Python 3.10
* Conda environment (recommended)
* GPU (optional, for faster YOLO inference)

---

## 🚀 Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/VijayRajput4455/DishGinee.git
cd DishGinee
```

### 2. Set Up Backend

```bash
conda create --name dishginee python=3.10
conda activate dishginee
pip install -r requirements.txt
```

### 3. Run Backend Server

```bash
uvicorn app.main:app --reload
```

---

## 📷 Sample Workflow

1. Upload one or more food images
2. YOLO detects all food items
3. System predicts 5 personalized recipes
4. Select a recipe
5. View step-by-step instructions & nutrition details
6. Optional ingredients suggested to enhance the dish

---

## 📌 Future Enhancements

* Multi-language recipe support
* Voice-guided cooking instructions
* Integration with grocery delivery services
* Personalized diet recommendations

---

✅ **Notes / Tips**:

* Ensure `models/` folder contains the YOLO weights (`Veg_best.pt`).
* Images should be `.jpg` or `.png`.
* Uvicorn `--reload` automatically refreshes backend on code changes.
