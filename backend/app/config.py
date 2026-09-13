from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.engine import URL

REPO_ROOT = Path(__file__).resolve().parents[2]


def load_env() -> None:
    load_dotenv(REPO_ROOT / ".env")


def postgres_url() -> URL:
    import os

    load_env()
    return URL.create(
        "postgresql+psycopg2",
        username=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        host=os.environ["POSTGRES_HOST"],
        port=int(os.environ["POSTGRES_PORT"]),
        database=os.environ["POSTGRES_DB"],
    )


def dev_case_creator_email() -> str:
    """Email of the development-only placeholder used as cases.created_by.

    Not authentication. Replace with the JWT subject when auth is implemented.
    """
    import os

    load_env()
    return os.environ.get("DEV_CASE_CREATOR_EMAIL", "dev-creator@crimelens.local")


def upload_dir() -> Path:
    """Local evidence file store. Files are named by document UUID only."""
    import os

    load_env()
    raw = os.environ.get("UPLOAD_DIR", "./data/uploads")
    path = Path(raw)
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path.resolve()


def max_upload_bytes() -> int:
    import os

    load_env()
    return int(os.environ.get("MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))


def neo4j_settings() -> tuple[str, str, str]:
    """Return (uri, user, password) from environment. Never log the password."""
    import os

    load_env()
    return (
        os.environ["NEO4J_URI"],
        os.environ["NEO4J_USER"],
        os.environ["NEO4J_PASSWORD"],
    )
