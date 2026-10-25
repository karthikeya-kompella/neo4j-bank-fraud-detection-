"""Load the CSVs from ./data into Neo4j.

Run from the project root:
    python -m scripts.load_graph            # wipes the graph and reloads
"""
import csv
import time
from pathlib import Path

from app.db import close_driver, get_driver

DATA = Path("data")
BATCH = 1000

CONSTRAINTS = [
    "CREATE CONSTRAINT customer_id IF NOT EXISTS FOR (c:Customer) REQUIRE c.id IS UNIQUE",
    "CREATE CONSTRAINT account_id IF NOT EXISTS FOR (a:Account) REQUIRE a.id IS UNIQUE",
    "CREATE CONSTRAINT device_id IF NOT EXISTS FOR (d:Device) REQUIRE d.id IS UNIQUE",
    "CREATE CONSTRAINT phone_id IF NOT EXISTS FOR (p:Phone) REQUIRE p.id IS UNIQUE",
    "CREATE CONSTRAINT address_id IF NOT EXISTS FOR (a:Address) REQUIRE a.id IS UNIQUE",
    "CREATE INDEX transfer_ts IF NOT EXISTS FOR ()-[t:TRANSFERRED]-() ON (t.ts)",
]

LOAD_CUSTOMERS = """
UNWIND $rows AS row
MERGE (c:Customer {id: row.id})
SET c.name = row.name, c.signup_ts = row.signup_ts
"""

LOAD_ACCOUNTS = """
UNWIND $rows AS row
MATCH (c:Customer {id: row.customer_id})
MERGE (a:Account {id: row.id})
SET a.opened_ts = row.opened_ts
MERGE (c)-[:OWNS]->(a)
"""

# One query per identifier kind: labels and relationship types can't be parameters in Cypher.
LOAD_IDENTIFIERS = {
    "Device": """
        UNWIND $rows AS row
        MATCH (c:Customer {id: row.customer_id})
        MERGE (x:Device {id: row.value})
        MERGE (c)-[:USES]->(x)""",
    "Phone": """
        UNWIND $rows AS row
        MATCH (c:Customer {id: row.customer_id})
        MERGE (x:Phone {id: row.value})
        MERGE (c)-[:HAS_PHONE]->(x)""",
    "Address": """
        UNWIND $rows AS row
        MATCH (c:Customer {id: row.customer_id})
        MERGE (x:Address {id: row.value})
        MERGE (c)-[:HAS_ADDRESS]->(x)""",
}

LOAD_TRANSFERS = """
UNWIND $rows AS row
MATCH (a:Account {id: row.src}), (b:Account {id: row.dst})
CREATE (a)-[:TRANSFERRED {id: row.id, amount: row.amount, ts: row.ts}]->(b)
"""


def read_csv(name: str) -> list[dict]:
    with open(DATA / name, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def batches(rows: list[dict]):
    for i in range(0, len(rows), BATCH):
        yield rows[i : i + BATCH]


def load(session, cypher: str, rows: list[dict], label: str):
    t0 = time.time()
    for chunk in batches(rows):
        session.run(cypher, rows=chunk).consume()
    print(f"  {label:<14} {len(rows):>6} rows  ({time.time() - t0:.1f}s)")


def main():
    customers = read_csv("customers.csv")
    for r in customers:
        r["signup_ts"] = int(r["signup_ts"])

    accounts = read_csv("accounts.csv")
    for r in accounts:
        r["opened_ts"] = int(r["opened_ts"])

    identifiers = read_csv("identifiers.csv")

    transfers = read_csv("transfers.csv")
    for r in transfers:
        r["amount"] = float(r["amount"])
        r["ts"] = int(r["ts"])

    with get_driver().session() as session:
        print("Wiping existing graph...")
        session.run("MATCH (n) DETACH DELETE n").consume()

        print("Creating constraints and indexes...")
        for stmt in CONSTRAINTS:
            session.run(stmt).consume()

        print("Loading data...")
        load(session, LOAD_CUSTOMERS, customers, "customers")
        load(session, LOAD_ACCOUNTS, accounts, "accounts")
        for kind, cypher in LOAD_IDENTIFIERS.items():
            rows = [r for r in identifiers if r["kind"] == kind]
            load(session, cypher, rows, kind.lower() + "s")
        load(session, LOAD_TRANSFERS, transfers, "transfers")

    close_driver()
    print("Done. Open http://localhost:7474 to explore, or start the API.")


if __name__ == "__main__":
    main()
