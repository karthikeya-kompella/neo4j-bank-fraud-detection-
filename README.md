# Neo4j Bank Fraud Detection

**A graph-based fraud detection system built with Neo4j, Cypher, Python, and FastAPI.**

Identify suspicious banking activity by modeling customers, accounts, identifiers, and money transfers as a connected graph. Analyze relationships between entities to uncover potential fraud rings, circular transactions, shared identifiers, and money mule activity.

## Overview

Traditional fraud detection systems often analyze transactions individually or rely on predefined rules. However, fraudulent activity can involve multiple accounts and customers connected through complex transaction networks.

This project uses **Neo4j's graph database** to represent banking entities and their relationships, enabling relationship-based analysis to identify suspicious patterns that may be difficult to detect using isolated transaction records.

The system includes synthetic banking data generation, graph data loading, Cypher-based detection queries, and an API layer built with FastAPI.

## Key Features

- **Graph-Based Fraud Analysis:** Model customers, bank accounts, identifiers, and transfers as interconnected graph entities.
- **Fraud Ring Detection:** Identify groups of customers or accounts connected through shared relationships.
- **Circular Transaction Detection:** Detect potential cycles in money-transfer networks.
- **Shared Identifier Analysis:** Flag entities that share identifiers, which may warrant further investigation.
- **Money Mule Identification:** Explore suspicious account and transaction relationships associated with potential money mule activity.
- **Synthetic Data Generation:** Generate test banking data with planted suspicious patterns for evaluating detection logic.
- **REST API:** Expose fraud detection functionality through FastAPI.
- **Graph Database Integration:** Use Neo4j and Cypher to query relationships and patterns efficiently.
- **Evaluation Pipeline:** Run project evaluation scripts against generated graph data.

## Tech Stack

| Technology | Purpose |
|---|---|
| Python | Core application logic and data processing |
| Neo4j | Graph database and relationship analysis |
| Cypher | Graph queries and fraud pattern detection |
| FastAPI | REST API layer |
| Uvicorn | ASGI server |
| Docker Compose | Run the Neo4j database |
| Neo4j Python Driver | Connect Python applications to Neo4j |

## Architecture

```text
Synthetic Banking Data
          |
          v
    Data Generation
          |
          v
    Graph Data Loader
          |
          v
       Neo4j
  (Nodes & Relationships)
          |
          v
   Cypher Detection Queries
          |
          v
   Fraud Detection Logic
          |
          v
       FastAPI
          |
          v
   Detection Results
```

## Graph Data Model

The system represents banking information as a graph.

### Entities

- **Customer:** Represents a banking customer.
- **Account:** Represents a bank account.
- **Identifier:** Represents a shared identifier associated with entities, such as a phone number or other identifier, depending on the implemented data model.
- **Transfer:** Represents a money transfer between accounts, if modeled as a separate graph entity in the implementation.

### Relationships

Relationships connect customers, accounts, identifiers, and transfers. The exact relationship types depend on the graph-loading implementation.

This graph structure makes it possible to investigate connections across multiple entities rather than examining each transaction independently.

## Project Structure

```text
neo4j-bank-fraud-detection-/
├── app/
│   ├── main.py              # FastAPI application
│   ├── db.py                # Neo4j database connection helpers
│   ├── queries.py           # Cypher query definitions
│   └── detection.py         # Fraud detection logic
├── scripts/
│   ├── generate_data.py     # Generate synthetic banking data
│   ├── load_graph.py        # Load data into Neo4j
│   └── evaluate.py          # Evaluate detection results
├── docker-compose.yml       # Neo4j container configuration
├── requirements.txt         # Python dependencies
├── .env                     # Local environment variables (not committed)
├── .gitignore
└── README.md
```

*The directory structure above reflects the project layout; adjust filenames if your implementation differs.*

## Getting Started

### Prerequisites

Install the following:

- Python 3.10 or later
- Docker Desktop
- Git

### 1. Clone the Repository

```bash
git clone https://github.com/karthikeya-kompella/neo4j-bank-fraud-detection-.git
cd neo4j-bank-fraud-detection-
```

### 2. Start Neo4j

Make sure Docker Desktop is running, then execute:

```bash
docker compose up -d
```

Check the running containers:

```bash
docker compose ps
```

Open the Neo4j Browser:

[http://localhost:7474](http://localhost:7474)

Use the Neo4j credentials configured in your local Docker Compose and environment settings.

### 3. Create a Virtual Environment

**Windows PowerShell**

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Linux / macOS**

```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Configure Environment Variables

Create a local `.env` file in the project root and configure the connection settings to match your Neo4j setup.

```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_local_password
```

Replace `your_local_password` with the password configured for your local Neo4j instance. Never commit real credentials or API keys.

### 6. Generate Synthetic Data

```bash
python -m scripts.generate_data
```

This generates the synthetic banking dataset used by the project.

### 7. Load the Graph

```bash
python -m scripts.load_graph
```

This loads the generated data into Neo4j so that the graph queries can analyze its entities and relationships.

### 8. Run the Evaluation

```bash
python -m scripts.evaluate
```

Use the evaluation output to inspect the detection logic against the planted suspicious patterns in the synthetic dataset.

### 9. Start the API

```bash
uvicorn app.main:app --reload
```

Once the application starts, open:

- **API base URL:** [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Interactive API documentation:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

The available endpoints depend on the routes implemented in `app/main.py`.

## Fraud Detection Approach

The project focuses on detecting suspicious patterns through graph relationships.

### 1. Fraud Rings

Investigate groups of connected entities that may share accounts, identifiers, or transaction links.

### 2. Circular Transactions

Analyze transfer paths that return to an earlier account or entity. Such cycles can be suspicious, although legitimate activity can also form cycles.

### 3. Shared Identifiers

Find customers or accounts linked through common identifiers. These connections can reveal potentially related entities that deserve additional review.

### 4. Potential Money Mules

Analyze account relationships and transaction patterns that may indicate intermediary accounts used to move funds.

**Important:** These patterns are investigation signals, not proof of fraud. Real-world deployment would require additional validation, risk scoring, and human review.

## Evaluation

The project includes an evaluation script and synthetic data with deliberately planted suspicious patterns.

The data-generation output reports the following configured dataset statistics:

| Metric | Generated count |
|---|---:|
| Customers | 2,000 |
| Accounts | 2,497 |
| Identifiers | 6,006 |
| Transfers | 8,093 |
| Planted fraud rings | 6 |
| Planted cycles | 12 |
| Planted money mules | 3 |

These are synthetic dataset generation counts, not measured detection accuracy. Actual precision, recall, false-positive rate, and detection coverage should be reported only after running and validating the evaluation pipeline.

## Security Considerations

- Keep `.env` and other secret-bearing files out of version control.
- Use strong credentials for any non-local Neo4j deployment.
- Do not expose database ports publicly without appropriate network controls.
- Use synthetic or properly anonymized data for development and demonstrations.
- Validate detection results before making decisions that affect real customers.

## Future Enhancements

Potential extensions include:

- Risk scoring for suspicious customers and accounts.
- Interactive graph visualization of fraud networks.
- Time-window analysis of transaction patterns.
- Additional Cypher-based detection rules.
- Precision, recall, and false-positive evaluation metrics.
- Authentication and authorization for API endpoints.
- Monitoring, structured logging, and deployment automation.

## Disclaimer

This project is intended for educational, research, and demonstration purposes. It uses synthetic banking data and does not constitute a production-ready financial crime detection system.

## Author

**Karthikeya Kompella**

GitHub: [@karthikeya-kompella](https://github.com/karthikeya-kompella)

---

*Built to explore graph databases, relationship-driven analytics, and fraud detection using Neo4j and Python.*
