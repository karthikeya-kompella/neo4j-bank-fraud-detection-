"""Neo4j connection helpers (one shared driver for the whole process)."""
import os

from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
USER = os.getenv("NEO4J_USER", "neo4j")
PASSWORD = os.getenv("NEO4J_PASSWORD", "fraudgraph123")

_driver = None


def get_driver():
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))
    return _driver


def close_driver():
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None


def run_read(cypher: str, **params) -> list[dict]:
    """Run a read query in a managed read transaction (auto-retries on transient errors)."""

    def work(tx):
        return [record.data() for record in tx.run(cypher, **params)]

    with get_driver().session() as session:
        return session.execute_read(work)


def run_write(cypher: str, **params) -> list[dict]:
    def work(tx):
        return [record.data() for record in tx.run(cypher, **params)]

    with get_driver().session() as session:
        return session.execute_write(work)
