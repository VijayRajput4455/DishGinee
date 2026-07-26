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

## 🚀 Getting Started (Running Locally)

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running.
- Python 3.10+ (optional, for local development outside Docker).

---

### 1. Configure Environment Variables
Copy the `.env.example` template to create your local `.env` file:

```bash
# On Linux / macOS / Git Bash
cp .env.example .env

# On Windows PowerShell
Copy-Item .env.example .env
```

---

### 2. Run the Entire Application Stack with Docker

To build and start all services (PostgreSQL, RabbitMQ, Redis, MinIO, Ollama, FastAPI Backend, Background Worker, and Nginx Frontend):

```bash
docker compose -f docker/docker-compose.yml up -d --build
```

---

### 🌐 Accessing Services

Once all containers are running, you can access the following services:

| Service | URL / Port | Description |
| :--- | :--- | :--- |
| **Web Frontend UI** | [http://localhost:80](http://localhost:80) | Main User Interface |
| **FastAPI Backend & API Docs** | [http://localhost:8000/docs](http://localhost:8000/docs) | Interactive Swagger API Documentation |
| **MinIO Console** | [http://localhost:9001](http://localhost:9001) | Object Storage Web Dashboard (`dishgenie_minioadmin` / `dishgenie_miniopassword`) |
| **RabbitMQ Management** | [http://localhost:15672](http://localhost:15672) | Queue Dashboard (`dishgenie_rmq_user` / `dishgenie_rmq_password`) |
| **Ollama Local LLM** | [http://localhost:11434](http://localhost:11434) | Local LLM Engine Endpoint |

---

### 📋 Useful Docker Commands

- **View Live Container Logs:**
  ```bash
  docker compose -f docker/docker-compose.yml logs -f
  ```

- **View Logs for Specific Services (e.g., App & Worker):**
  ```bash
  docker compose -f docker/docker-compose.yml logs -f app worker
  ```

- **Check Container Status:**
  ```bash
  docker compose -f docker/docker-compose.yml ps
  ```

- **Stop All Application Services:**
  ```bash
  docker compose -f docker/docker-compose.yml down
  ```

- **Stop & Remove All Volumes (Clean Reset):**
  ```bash
  docker compose -f docker/docker-compose.yml down -v
  ```

---

### 🛠️ Alternative: Run Infrastructure Only (Local Dev Mode)

If you are developing backend code locally and only want to run database and message services via Docker:

1. **Start Infrastructure Containers:**
   ```bash
   docker compose -f docker/docker-compose.yml up -d postgres rabbitmq redis minio create-bucket ollama
   ```

2. **Install Dependencies & Run FastAPI App:**
   ```bash
   pip install -r requirements.txt
   uvicorn app.main:app --reload --port 8000
   ```

3. **Run Background Worker:**
   ```bash
   python -m app.workers.task_worker
   ```

