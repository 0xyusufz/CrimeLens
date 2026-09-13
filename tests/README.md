# Tests

```bash
cd /path/to/CrimeLens
source backend/.venv/bin/activate
PYTHONPATH=. python tests/test_ml_contract.py
PYTHONPATH=. python tests/test_postgres.py
```

`test_ml_contract.py` does not connect to databases.
`test_postgres.py` uses CrimeLens PostgreSQL from `.env` (host port 5433).
