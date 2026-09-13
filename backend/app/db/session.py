from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import postgres_url

engine = create_engine(postgres_url(), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
