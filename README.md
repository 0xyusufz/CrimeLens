# CrimeLens

**CrimeLens** is an enterprise-grade, AI-powered criminal investigation and intelligence graph platform. It automates the end-to-end evidence pipeline—from unstructured case file ingestion and forensic document OCR to automated entity-relationship extraction, Neo4j knowledge graph construction, cryptographic chain-of-custody tracking, and grounded conversational intelligence.

---

## The Problem

> **Criminal investigation data is fragmented across FIRs, CDRs, financial records, surveillance, and social media, making hidden connections difficult and time-consuming to identify manually.**

Modern law enforcement agencies and investigative bodies face critical operational bottlenecks:

- **Fragmented Data Silos**: Case evidence arrives in heterogeneous, unstructured formats—First Information Reports (FIRs), interrogation transcripts, witness testimonies, Call Detail Records (CDRs), bank transaction logs, and forensic lab reports.
- **Manual Cognitive Overload**: Investigators must manually cross-reference hundreds of document pages to uncover common telephone numbers, vehicle registrations, shared aliases, and intermediary contacts.
- **Hidden Link Blindness**: Complex criminal syndicates operate across multi-layered networks. Multi-hop connections (e.g., *Suspect A -> Shared Courier -> Anonymous Alias -> Victim B*) remain obscured in traditional linear document reviews.
- **Chain-of-Custody & Evidence Integrity**: Maintaining tamper-evident, court-admissible audit trails for digital evidence requires cryptographic immutability from initial upload to final court presentation.

---

## The CrimeLens Solution

CrimeLens unifies fragmented forensic evidence into a single, cohesive, graph-powered intelligence environment:

1. **Automated Evidence Ingestion & Parsing**: Ingests multi-page PDFs, scanned documents, plain text, and structured CSV records with intelligent OCR and document structure extraction.
2. **Multi-Tier Entity & Relationship Extraction**: Utilizes a tiered extraction pipeline combining high-precision regex/heuristics, Named Entity Recognition (NER), and large language models (Groq LLaMA / OpenAI / Gemini) to extract canonical entities and typed relationships with verbatim text evidence anchors.
3. **Case Entity Consolidation & Disambiguation**: Performs automated deduplication, alias resolution, and cross-document entity clustering to build an accurate identity web.
4. **Dynamic Neo4j Crime Knowledge Graph**: Automatically projects consolidated entities and relationships into an interactive Neo4j graph database with strict schema integrity constraints.
5. **In-Sidebar AI Copilot & Dossier Engine**: Delivers real-time, context-grounded intelligence directly inside the investigation workspace—enabling investigators to run automated dossiers, trace communication paths, and ask forensic questions regarding specific suspects and links.
6. **Cryptographic Evidence Ledger**: Computes SHA-256 hashes and maintains a tamper-evident audit ledger in PostgreSQL for verifiable chain of custody.

---

## Technology Stack

| Layer | Technologies |
|---|---|
| **Frontend** | Next.js 14, React 18, ReactFlow, Custom Responsive CSS (Glassmorphism / Tactical Dark & Light UI) |
| **Backend API** | FastAPI (Python 3.10+), Pydantic v2, SQLAlchemy ORM, Uvicorn ASGI Server |
| **Graph Database** | Neo4j 5.x (Cypher Query Language, Bolt Protocol) |
| **Relational & Ledger DB** | PostgreSQL 16 (Relational Metadata, Staging Tables, SHA-256 Evidence Chain) |
| **AI / NLP & Reasoning** | Multi-tier Extraction Pipeline, Groq API (LLaMA 3.3 / GPT-OSS), Gemini Intelligence, PyMuPDF / Tesseract OCR |
| **Authentication & Security** | JWT (JSON Web Tokens), OAuth2 Password Bearer, PBKDF2/Bcrypt Password Hashing |
| **Containerization** | Docker, Docker Compose |

---

## System Capabilities

### 1. Unified Case Management
- Organize investigations into isolated cases with role-based access control.
- Track case metadata, priority, lead investigators, and live case statistics (total entities, verified connections, document counts).

### 2. Multi-Format Evidence Ingestion
- Ingest PDFs (scanned or native text), FIR documents, forensic lab reports, interrogation summaries, and CDR/financial spreadsheets.
- Automatic text extraction, chunking, and hash generation for cryptographic evidence verification.

### 3. Entity Resolution & Knowledge Graph Projection
- Identifies and classifies key entity types: `Person`, `Organization`, `Location`, `Vehicle`, `Phone`, `BankAccount`, and `Event`.
- Extracts relational ties: `ASSOCIATED_WITH`, `WORKS_FOR`, `LOCATED_AT`, `OWNS_VEHICLE`, `USED_VEHICLE`, `CALLED`, `SENT_MONEY_TO`, `PART_OF_EVENT`.
- Automated graph projection with deduplication to ensure canonical identities are merged cleanly.

### 4. Interactive Visual Graph Canvas
- Node-link visualization powered by ReactFlow with automatic degree-based radial and force-directed layouts.
- **Focus Mode**: Isolate suspect networks, filter secondary connections, and center on key nodes.
- **Inspector Panel**: Detailed inspection of entity attributes, aliases, associated cases, and cited document anchors.
- **In-Sidebar AI Chat**: Query case intelligence on any selected entity or connection directly within the inspector panel.

### 5. Multi-Hop Pathfinding & Intelligence Dossiers
- Shortest-path and multi-hop relationship discovery between suspects, intermediaries, and assets.
- One-click comprehensive AI Dossier generation summarizing network threats, points of interest, key evidentiary anchors, and investigative leads.

### 6. Cryptographic Chain-of-Custody Ledger
- Tamper-evident ledger recording all document uploads, processing runs, entity modifications, and user actions.
- Verifiable SHA-256 document hashing ensures court-admissible evidence authenticity.

---

## Quick Start Guide

### 1. Prerequisites
- **Docker & Docker Compose** (for PostgreSQL and Neo4j)
- **Python 3.10+**
- **Node.js 18+** and **npm**

---

### 2. Environment Configuration

Copy the example environment configuration file to `.env`:

```bash
cp .env.example .env
```

Ensure the following variables are configured in `.env`:

```env
# Database Credentials
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=crimelens
POSTGRES_PORT=5433

NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=crimelens_password

# Authentication
SECRET_KEY=your_secure_random_jwt_secret_key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# AI Provider Keys (Optional for Cloud AI Models)
GROQ_API_KEY=your_groq_api_key
GEMINI_API_KEY=your_gemini_api_key
```

---

### 3. Start Database Containers

Launch PostgreSQL and Neo4j services in the background:

```bash
docker compose up -d
```

- **PostgreSQL**: `localhost:5433`
- **Neo4j Browser**: `http://localhost:7474` (Bolt: `bolt://localhost:7687`)

---

### 4. Backend Setup & Startup

```bash
cd backend

# Create and activate virtual environment
python -m venv .venv

# On Windows:
.venv\Scripts\activate
# On Linux / macOS:
# source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Initialize database schema and default developer credentials:
python scripts/init_dev_data.py

# Start the FastAPI ASGI server:
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- **Backend API Base URL**: `http://localhost:8000`
- **Interactive OpenAPI Documentation**: `http://localhost:8000/docs`

---

### 5. Frontend Setup & Startup

In a separate terminal:

```bash
cd frontend

# Install Node dependencies
npm install

# Start Next.js development server
npm run dev
```

- **Frontend Application URL**: `http://localhost:3000`

---

### Default Credentials
- **Username / Email**: `dev@crimelens.local`
- **Password**: `password`

---

## Core API Endpoints

All endpoints (except `/api/auth/login`) require standard Bearer token authentication header: `Authorization: Bearer <token>`.

### Authentication
- `POST /api/auth/login` — Authenticate credentials and receive JSON Web Token (JWT).

### Case Management
- `GET /api/cases` — List all active investigation cases for the authenticated user.
- `POST /api/cases` — Initialize a new criminal investigation case.
- `GET /api/cases/{case_id}` — Retrieve case overview, summary, and aggregate statistics.

### Document & Evidence Ingestion
- `POST /api/cases/{case_id}/documents` — Upload evidentiary files (PDFs, images, TXT, CSV).
- `GET /api/cases/{case_id}/documents` — List uploaded case documents and their processing statuses.
- `POST /api/documents/{document_id}/process` — Trigger OCR, entity-relationship extraction, and Neo4j graph projection.

### Knowledge Graph & Investigation
- `GET /api/cases/{case_id}/graph` — Retrieve full canonical node and relationship graph for visualization.
- `POST /api/investigation/path` — Query shortest or multi-hop connection paths between two entities.
- `GET /api/relationships/{rel_id}/evidence` — Fetch verbatim text citations and source document anchors for a relationship.

### AI Intelligence & Copilot
- `POST /api/cases/{case_id}/copilot` — Query the forensic AI Copilot with case-grounded context.
- `POST /api/cases/{case_id}/intelligence/analyze` — Trigger full case network AI reasoning and threat analysis.
- `GET /api/cases/{case_id}/intelligence/analyze/status` — Fetch the latest investigative intelligence dossier.

### Chain of Custody & Audit
- `GET /api/cases/{case_id}/evidence-ledger` — Audit the tamper-evident SHA-256 cryptographic evidence ledger.

---

## License

This project is licensed under the MIT License.
