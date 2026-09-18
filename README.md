# CrimeLens

CrimeLens is an AI-powered criminal investigation and intelligence platform. It automates evidence processing from unstructured case documents (FIRs, forensics reports, call detail records, financial statements), extracts entities and relationships, constructs connected crime knowledge graphs in Neo4j, maintains a tamper-evident SHA-256 evidence ledger in PostgreSQL, and offers interactive visual graph analysis, multi-hop investigation pathfinding, and an AI copilot.

---

## Tech Stack

- **Frontend**: Next.js 14, React, ReactFlow, Vanilla CSS
- **Backend**: FastAPI (Python 3.10+), SQLAlchemy, Uvicorn
- **Databases**: PostgreSQL (Relational & Evidence Ledger), Neo4j (Graph Intelligence Layer)
- **AI / ML**: Multi-tier extraction (OCR, regex/heuristics, Groq LLaMA, Gemini Copilot)

---

## Quick Start Guide

### 1. Prerequisites
- Docker & Docker Compose
- Python 3.10+
- Node.js 18+ and npm

---

### 2. Environment Setup

Copy `.env.example` to `.env` in the root directory:

```bash
cp .env.example .env
```

*(Optional: Set `GROQ_API_KEY` or `GEMINI_API_KEY` in `.env` if you wish to enable cloud AI models).*

---

### 3. Start Databases (Docker)

Start PostgreSQL and Neo4j containers in background:

```bash
docker compose up -d
```

- **PostgreSQL**: `localhost:5433`
- **Neo4j Browser**: `http://localhost:7474` (Bolt: `bolt://localhost:7687`)

---

### 4. Start Backend Server (FastAPI)

```bash
cd backend
python -m venv .venv

# On Windows:
.venv\Scripts\activate
# On Linux / macOS:
# source .venv/bin/activate

pip install -r requirements.txt

# Run migrations / seed dev user:
python scripts/init_dev_data.py

# Start the API server:
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- **Backend URL**: `http://localhost:8000`
- **Interactive API Docs (Swagger UI)**: `http://localhost:8000/docs`

---

### 5. Start Frontend Server (Next.js)

In a separate terminal:

```bash
cd frontend
npm install
npm run dev
```

- **Frontend URL**: `http://localhost:3000`

---

### Default Dev Credentials
- **Email**: `dev@crimelens.local`
- **Password**: `password`

---

## Core API Endpoints Overview

All endpoints (except `/api/auth/login`) require `Authorization: Bearer <token>`.

| Endpoint | Method | Description |
|---|---|---|
| `/api/auth/login` | POST | Login and receive JWT access token |
| `/api/cases` | GET / POST | List user cases or create a new investigation case |
| `/api/cases/{case_id}` | GET | Get case details, statistics, and summary |
| `/api/cases/{case_id}/documents` | POST | Upload case files (PDFs, images, TXT) |
| `/api/documents/{doc_id}/process` | POST | Run OCR, entity/relation extraction, and Neo4j graph projection |
| `/api/cases/{case_id}/graph` | GET | Retrieve connected entities and relationship graph |
| `/api/investigation/path` | POST | Query shortest/multi-hop path between two entities |
| `/api/cases/{case_id}/copilot` | POST | Query AI Copilot for case analysis and intelligence insights |
| `/api/cases/{case_id}/evidence-ledger` | GET | View cryptographic SHA-256 evidence integrity ledger chain |

For full request/response schemas and live testing, visit **`http://localhost:8000/docs`**.
