# CrimeLens

4-day SIH-style MVP for investigation support.

## Architecture

```
Next.js
   ↓
FastAPI
   ↓
PostgreSQL + Neo4j
```

- **PostgreSQL** is the source of truth.
- **Neo4j** is a derived graph / relationship intelligence layer.
- **Person B ML pipeline** produces structured JSON only. It never writes to PostgreSQL or Neo4j. FastAPI validates and persists that JSON.

## Ownership

| Person | Owns |
| --- | --- |
| A | Git, Docker Compose, FastAPI, PostgreSQL, Neo4j, graph queries, multi-hop investigation, Next.js, JWT, RBAC, case-level authorization, audit logging, SHA-256 evidence integrity, hash-linked evidence ledger, ML-output validation, ML/backend integration |
| B | OCR, NER/entity extraction, relationship extraction, entity-resolution proposals, suspicious pattern detection, ML JSON output |

## Local setup (skeleton)

1. Copy environment placeholders:

   ```bash
   cp .env.example .env
   ```

2. Start databases:

   ```bash
   docker compose up -d
   ```

3. Backend (after creating a virtualenv):

   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

4. Frontend:

   ```bash
   cd frontend
   npm install
   npm run dev
   ```

Business logic, models, and API contracts are not implemented in this skeleton.
