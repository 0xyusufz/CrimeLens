# Tests

```bash
cd /path/to/CrimeLens
source backend/.venv/bin/activate
PYTHONPATH=. python tests/test_ml_contract.py
```

These tests validate ML JSON contracts only. They do not connect to PostgreSQL or Neo4j.
