# Backend (Person A)

FastAPI + PostgreSQL (source of truth). Neo4j is not used in this layer yet.

The ML pipeline must not write to PostgreSQL or Neo4j.

## Database

Connection settings come from the repo-root `.env` (`POSTGRES_*`). CrimeLens Postgres is on host port **5433**.

```bash
cd backend
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
```
