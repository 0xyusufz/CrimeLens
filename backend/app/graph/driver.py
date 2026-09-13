from neo4j import GraphDatabase

from app.config import neo4j_settings

_driver = None


def get_driver():
    """Shared Neo4j driver. Neo4j is a derived graph layer, not source of truth."""
    global _driver
    if _driver is None:
        uri, user, password = neo4j_settings()
        _driver = GraphDatabase.driver(uri, auth=(user, password))
    return _driver


def close_driver() -> None:
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None
