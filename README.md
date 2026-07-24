# 🧙‍♂️ DishGenie – AI-Powered Smart Recipe Generation Platform

DishGenie is a production-ready AI backend built with **FastAPI**, **PostgreSQL**, **SQLAlchemy 2.0**, **RabbitMQ**, **MinIO**, **Docker**, and **Large Language Models (LLMs)**.

The platform allows users to generate recipes using three input methods:
* 📷 **Image Upload** (YOLO ingredient detection)
* 📝 **Manual Ingredient Entry**
* 🎤 **Voice Input** (Whisper Speech-to-Text)

---

## 🏗️ Architecture & Features

- **Clean Architecture**: Domain models, schemas, repositories, services, and worker layers decoupled for scalability.
- **Event-Driven Processing**: Asynchronous workers processing heavy CV (YOLO) and Audio (Whisper) models via **RabbitMQ**.
- **Object Storage**: Direct client upload and asset management powered by **MinIO**.
- **Database & Persistence**: **PostgreSQL** + **SQLAlchemy 2.0** with async/sync capabilities.

---

## 📂 Project Structure

```
DishGenie/
├── app/
│   ├── api/          # FastAPI routes & endpoints
│   ├── core/         # Settings, database session, security
│   ├── enums/        # Business logic enums (InputType, RequestStatus, ImageStatus)
│   ├── models/       # SQLAlchemy 2.0 ORM models (Request, RequestImage, RequestOutput)
│   ├── repositories/ # Data access layer
│   ├── schemas/      # Pydantic v2 schemas
│   ├── services/     # Core business logic services
│   └── workers/      # RabbitMQ async task consumers
├── .env.example      # Environment variables template
├── .gitignore        # Git ignore rules
└── README.md
```

---

## 🚀 Getting Started

### 1. Clone & Setup
```bash
cp .env.example .env
```

### 2. Run Database & Infrastructure Services
```bash
docker compose up -d
```
