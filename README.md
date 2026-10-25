# Graph Fraud Ring Detector (Neo4j + FastAPI)

Detects organised fraud in a banking network by treating it as a **graph** instead of rows in tables.
Three fraud patterns that are painful in SQL (multi-way self-joins) are short Cypher queries here:

| Pattern | What it means | Graph idea |
|---|---|---|
| **Fraud rings** | Many "different" customers share a device / phone / address | Connected components over shared-identity edges (Cypher + Union-Find) |
| **Circular transfers** | Money goes A -> B -> C -> A to hide its origin (layering) | Variable-length path that returns to its start, time-ordered |
| **Mule accounts** | Many small deposits in, almost everything out within hours | Fan-in / fan-out degree and flow analysis |

A 0-100 **risk score** combines the three signals and lists the reasons, so every flag is explainable.

## Graph model

```
(:Customer)-[:OWNS]->(:Account)-[:TRANSFERRED {amount, ts}]->(:Account)
(:Customer)-[:USES]->(:Device)
(:Customer)-[:HAS_PHONE]->(:Phone)
(:Customer)-[:HAS_ADDRESS]->(:Address)
```

## Run it

Needs Docker and Python 3.10+.

```bash
# 1. Start Neo4j (Browser at http://localhost:7474, login neo4j / fraudgraph123)
docker compose up -d

# 2. Python env
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. Generate synthetic data with PLANTED fraud, load it, measure detection
python -m scripts.generate_data --customers 2000 --seed 42
python -m scripts.load_graph
python -m scripts.evaluate

# 4. Start the API + visual UI
uvicorn app.main:app --reload
# UI:       http://localhost:8000
# API docs: http://localhost:8000/docs
```

Wait ~15 seconds after `docker compose up` before loading, Neo4j needs time to start.

## Project layout

```
app/queries.py     all Cypher, one place
app/detection.py   runs queries, Union-Find ring grouping, risk scoring
app/main.py        FastAPI endpoints (/rings /cycles /mules /risk /graph /stats)
app/static/        vis-network graph UI
scripts/           data generator, loader, evaluator
```

## Try these in Neo4j Browser (http://localhost:7474)

```cypher
// every customer in one ring, with what they share
MATCH (c:Customer)-[r:USES]->(d:Device)
WHERE d.id STARTS WITH 'DEV-R0'
RETURN c, r, d

// biggest shared devices
MATCH (c:Customer)-[:USES]->(d:Device)
WITH d, count(c) AS users WHERE users > 2
RETURN d.id, users ORDER BY users DESC

// loops of 3 transfers
MATCH p = (a:Account)-[:TRANSFERRED*3]->(a)
WHERE all(r IN relationships(p) WHERE r.amount > 5000)
RETURN p LIMIT 10
```

Use `PROFILE` or `EXPLAIN` in front of a query to see how Neo4j runs it. Reading that plan
is a good interview talking point.

## Resume bullets (fill in the real numbers after you run `scripts.evaluate`)

- Built a graph-based fraud detection system on **Neo4j** modelling customers, accounts, devices and
  transfers (N nodes, M relationships), exposing detection through a **FastAPI** service and an interactive graph UI.
- Wrote **Cypher** queries for fraud-ring discovery, time-ordered circular-transfer (layering) detection and
  mule-account fan-in/fan-out analysis; grouped linked identities with a **Union-Find** pass.
- Designed an explainable 0-100 customer risk score and validated detection on synthetic data with planted fraud,
  reaching X% precision and Y% recall.
- Tuned traversal queries with unique constraints, a relationship-property index and early predicate pruning,
  verified with `PROFILE`.

## Honest limitations (say these in interviews, they show maturity)

- Data is synthetic. Real fraud is noisier, so precision would be lower and thresholds need tuning.
- Cycle search with `*3..5` gets expensive on dense graphs. Production systems cap depth, use time windows or precompute.
- Shared identifiers like public Wi-Fi create false links, which is why `max_share` exists.
- No streaming ingestion. A real system would score transfers as they arrive.

## Ideas to extend later

- Neo4j **Graph Data Science**: Louvain community detection, PageRank, node similarity.
- Real-time scoring when a new transfer is inserted.
- Add a **recommendation** feature on the same database (customers who share merchants), the classic Neo4j use case.
