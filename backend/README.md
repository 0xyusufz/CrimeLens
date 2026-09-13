# Backend (Person A)

FastAPI + PostgreSQL (source of truth) + Neo4j (derived graph layer).

The ML pipeline must not write to PostgreSQL or Neo4j.

## Database

Connection settings come from the repo-root `.env`. CrimeLens Postgres is on host port **5433**. Neo4j Bolt is on **7687**.

```bash
cd backend
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
```

Neo4j schema constraints:

```bash
PYTHONPATH=. python -c "from app.graph import get_driver, init_schema; d=get_driver(); init_schema(d); d.close()"
```

Run that from `backend/` or with `PYTHONPATH=backend:.` from the repo root.
