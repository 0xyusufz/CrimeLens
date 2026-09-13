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
