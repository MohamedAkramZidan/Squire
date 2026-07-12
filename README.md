<div align="center">

# Squire

**From natural language to reliable execution — an AI-powered Mobile productivity assistant that transforms user requests into structured actions through intelligent language understanding, deterministic execution, and workflow automation.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10-3776AB?logo=python&logoColor=white)](backend/requirements.txt)
[![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi&logoColor=white)](backend/main.py)
[![Flutter](https://img.shields.io/badge/Flutter-Mobile-02569B?logo=flutter&logoColor=white)](mobile_app/pubspec.yaml)
[![PyTorch](https://img.shields.io/badge/PyTorch-Deep%20Learning-EE4C2C?logo=pytorch&logoColor=white)](NLU/train.py)
[![Hugging Face Transformers](https://img.shields.io/badge/Hugging%20Face-Transformers%20(NLU)-FFD21E?logo=huggingface&logoColor=black)](NLU/models/model.py)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-4169E1?logo=postgresql&logoColor=white)](backend/database/schema/DDL.sql)
[![Redis](https://img.shields.io/badge/Redis-Cache-DC382D?logo=redis&logoColor=white)](backend/database/redis_client.py)
[![n8n](https://img.shields.io/badge/n8n-Workflow%20Automation-EA4B71?logo=n8n&logoColor=white)](automation)
[![Docker](https://img.shields.io/badge/Docker-Containerization-2496ED?logo=docker&logoColor=white)](#)

</div>

---

## 📖 Overview

**Squire** is an end-to-end personal-productivity assistant. A user types (or speaks) a plain-language command — *"remind me to submit the report tomorrow at 5pm"* — and Squire:

1. Runs the sentence through a **custom-trained NLU model** to figure out the **intent** (`ADD`, `GET`, `UPDATE`, `DELETE`) and the **object** (`TASK`, `MEETING`, `NOTE`, `PROGRESS`), while tagging entities like dates, times, people, and locations.
2. **Post-processes and validates** the extracted entities (date/time normalization, field validation, ambiguity checks).
3. **Decides** whether it has enough information to act, or needs to ask a clarifying question.
4. **Executes** the resulting database operation and, where relevant, triggers **automation workflows** (Google Calendar events, email reminders via n8n).
5. **Responds** in natural language, generated with a lightweight local LLM.

The project is split into four cooperating pieces: an **NLU model**, a **FastAPI backend**, **n8n automation workflows**, and a **Flutter mobile app**.

---

---

## 📱 Mobile App

<p align="center">
  <img src="screenshots/chat1.png" alt="AI Chat" width="220">
  <img src="screenshots/chat2.png" alt="Conversation" width="220">
  <img src="screenshots/Calendar1.png" alt="Calendar View" width="220">
</p>

<p align="center">
  <img src="screenshots/Calendar2.png" alt="Calendar Event" width="220">
  <img src="screenshots/Google Calendar.png" alt="Google Calendar Integration" width="220">
  <img src="screenshots/email.png" alt="Email Reminder" width="220">
</p>

<p align="center">
  <em>AI Assistant • Calendar • Google Calendar Integration • Email Reminders</em>
</p>

---

## 🏗️ Architecture

<p align="center">
  <img src="docs/architecture/System%20Architecture%20Diagram.png" alt="Squire System Architecture" width="850">
</p>

**Request flow:** `Mobile App → FastAPI /predict → NLU (ONNX) → Postprocessing → Decision Engine → Executor (Postgres/Redis) → n8n Automation → LLM Response Generator → Mobile App`

---

## ✨ Features

- 🧠 **Custom NLU engine** — a transformer encoder (`microsoft/mdeberta-v3-base`) fine-tuned with lightweight **adapter layers** for joint intent classification + slot tagging, exported to **ONNX (INT8)** for fast CPU inference.
- 🔀 **4 actions × 4 objects** — Add / Get / Update / Delete across Tasks, Meetings, Notes, and Progress entries.
- 🗣️ **Entity extraction** for titles, dates, times, people, locations, statuses, fields/values, and free-text content.
- 🤔 **Clarification loop** — if a command is ambiguous (e.g., matches multiple tasks, or is missing a required field) Squire tracks conversation state in **Redis** and asks a follow-up question instead of guessing.
- 🔎 **RAG-powered notes** — notes are embedded (`all-MiniLM-L6-v2`) and stored in **Postgres + pgvector**; when you ask a question about your notes, Squire retrieves the top-matching chunks and feeds them to the LLM to generate a grounded answer (retrieval-augmented generation) instead of relying on the model's memory alone.
- 💬 **Local LLM response generation** (TinyLlama) for natural, human-sounding replies, RAG-based note Q&A, and task/progress summaries.
- 📅 **Automation** — n8n workflows push accepted tasks to Google Calendar and send email reminders ahead of deadlines.
- 📱 **Cross-platform mobile client** built with Flutter (Android, iOS, Web, Windows, Linux, macOS).

---

## 🗂️ Project Structure

```
Squire/
├── NLU/                 # Model training, evaluation, and ONNX export
│   ├── train.py
│   ├── inference.py
│   ├── export_onnx_int8.py
│   ├── models/           # Model architecture
│   ├── data/              # Dataset loading
│   ├── evaluation/        # Metrics
│   └── tools/audit_data.py
│
├── backend/              # FastAPI application (the core service)
│   ├── main.py
│   ├── api/routes.py            # HTTP endpoints
│   ├── services/                 # NLU inference, decision engine, execution, embeddings
│   ├── postprocess/               # Entity normalization & validation
│   ├── response/                  # LLM-based response generation + prompt templates
│   ├── database/                  # SQLAlchemy models, CRUD, DDL schema
│   ├── schemas/                   # Pydantic request/response models
│   └── config/                    # Settings & label definitions
│
├── automation/            # n8n workflow definitions (Calendar + reminders)
│
├── mobile_app/             # Flutter client application
│   └── lib/
│       ├── screens/          # Dashboard, Calendar, Curator (chat), Library
│       ├── services/          # squire_api.dart — HTTP client for the backend
│       ├── models/            # App state & data models
│       └── theme/             # App theming
│
├── data/                   # Training/raw datasets (ATIS, SNIPS, TopV2, custom)
├── docs/                    # Architecture diagram, ERD, database docs
├── experiments/              # Notebooks & scratch scripts
└── LICENSE
```

---

## 🧰 Tech Stack

| Layer | Technology |
|---|---|
| NLU Model | PyTorch, HuggingFace Transformers, `mdeberta-v3-base` + adapter layers, ONNX Runtime (INT8) |
| Backend API | FastAPI, Uvicorn, Pydantic |
| Database | PostgreSQL + `pgvector` (Docker) |
| Cache / Sessions | Redis (Docker) |
| Embeddings & RAG | Sentence-Transformers (`all-MiniLM-L6-v2`) + pgvector similarity search for grounded note retrieval |
| Response Generation | TinyLlama (local, via HuggingFace `transformers` pipeline) |
| Automation | n8n (Docker) — Google Calendar + Gmail workflows |
| Mobile Client | Flutter / Dart |

---

## 🚀 Getting Started

> All ports/URLs below (`localhost:5434`, `localhost:6379`, `localhost:5678`, `localhost:8000`) are local development defaults — swap them for your real hosts/ports in production.

### Prerequisites
- Python 3.10
- Docker (used to run PostgreSQL, Redis, and n8n)
- Flutter SDK (for the mobile app)

### 1. Infrastructure (Docker)

PostgreSQL (with `pgvector`), Redis, and n8n are run as Docker containers rather than installed locally:

```bash
# PostgreSQL with pgvector
docker run -d --name squire-postgres \
  -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=squire \
  -p 5434:5432 pgvector/pgvector:pg16

# Redis
docker run -d --name squire-redis -p 6379:6379 redis:7

# n8n
docker run -d --name squire-n8n -p 5678:5678 n8nio/n8n
```

Load the schema once Postgres is up:
```bash
psql -h localhost -p 5434 -U postgres -d squire -f backend/database/schema/DDL.sql
```

> Adjust ports/credentials as needed to match `DATABASE_URL`, `REDIS_URL`, and `N8N_WEBHOOK_URL` in the backend's `.env`.

### 2. Backend

```bash
cd backend
./setup.sh              # creates a venv, installs dependencies, sets up .env
# Edit .env with your database_url, redis_url, model_path, and n8n_webhook_url

uvicorn main:app --reload
```

Key configuration (see `backend/config/settings.py`) is supplied through a `.env` file:

| Variable | Purpose | Default |
|---|---|---|
| `MODEL_PATH` | Path to the exported ONNX NLU model | `models/squire_int8.onnx` |
| `ENCODER_MODEL` | Tokenizer/base encoder | `microsoft/mdeberta-v3-base` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+psycopg://postgres:postgres@localhost:5434/squire` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `N8N_WEBHOOK_URL` | Base URL for n8n webhooks | `http://localhost:5678/webhook` |
| `CREATE_TABLES_ON_STARTUP` | Auto-run schema creation on boot | `false` |

### 3. NLU Model

```bash
cd NLU
pip install -r requirements.txt

python train.py                  # adapter-based fine-tuning
python export_onnx_int8.py       # export + quantize to ONNX
python inference.py --text "schedule a meeting with Sara tomorrow at 3pm"
```

### 4. Automation (n8n)

1. Open your n8n dashboard at `http://localhost:5678` (from the Docker container above).
2. Import the workflow files from `automation/` (`Calendar Tasks.json`, `calendar-reminder-workflow.json`, `Google calendar workflow.json`).
3. Reconfigure the Google Calendar / Gmail credentials to your own accounts.
4. Activate the workflows. See `automation/README.md` for full details.

### 5. Mobile App

```bash
cd mobile_app
flutter pub get

# Point the app at your backend in lib/services/squire_api.dart:
#   Android Emulator → http://10.0.2.2:8000
#   iOS Simulator     → http://localhost:8000
#   Physical device   → http://<your-LAN-ip>:8000

flutter run
```

---

## 🔌 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/predict` | Main entry point — send raw text, get back NLU result, decision, execution outcome, and a natural-language response |
| `POST` | `/debug/raw` | Returns the raw NLU model output without post-processing/execution |
| `GET`  | `/debug/model` | NLU model metadata / health |
| `GET`  | `/health` | Service health check |
| `GET`  | `/api/tasks?user_id=` | List a user's tasks |
| `GET`  | `/api/meetings?user_id=` | List a user's meetings |
| `GET`  | `/api/notes?user_id=` | List a user's notes |
| `GET`  | `/api/progress?user_id=` | List a user's progress entries |

---

## 🗄️ Database

Squire uses PostgreSQL with the `pgvector` extension to store `users`, `tasks`, `meetings`, `notes`, and `progress`, each with an embedding column for semantic search.

<p align="center">
  <img src="docs/database/ERD.png" alt="Entity Relationship Diagram" width="700">
</p>

Full DDL: [`backend/database/schema/DDL.sql`](backend/database/schema/DDL.sql) · Additional docs: [`docs/database/`](docs/database)

---

---

## 🗺️ Roadmap

- [ ] Expand entity coverage (recurring events, priority levels)
- [ ] Voice input on mobile
- [ ] Multi-user / team workflows
- [ ] Swap TinyLlama for a larger local model for richer responses

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
