# Tests

```bash
cd /path/to/CrimeLens
source backend/.venv/bin/activate
PYTHONPATH=. python tests/test_ml_contract.py
PYTHONPATH=. python tests/test_postgres.py
PYTHONPATH=. python tests/test_neo4j.py
PYTHONPATH=. python tests/test_graph_projection.py
```

`test_ml_contract.py` does not connect to databases.
`test_postgres.py` uses CrimeLens PostgreSQL from `.env` (host port 5433).
`test_neo4j.py` uses CrimeLens Neo4j from `.env` (Bolt 7687). Neo4j is a derived graph layer.
`test_graph_projection.py` projects PostgreSQL canonical rows into Neo4j and cleans up both stores.
