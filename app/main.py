"""FastAPI service exposing the fraud-detection queries."""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import detection, queries as q
from app.db import close_driver, get_driver, run_read

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(_: FastAPI):
    get_driver().verify_connectivity()
    yield
    close_driver()


app = FastAPI(title="Graph Fraud Ring Detector", version="1.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health():
    get_driver().verify_connectivity()
    return {"status": "ok"}


@app.get("/stats")
def stats():
    return {"nodes": run_read(q.STATS), "relationships": run_read(q.REL_STATS)}


@app.get("/rings")
def rings(min_size: int = 3, max_share: int = 12):
    return detection.find_rings(min_size=min_size, max_share=max_share)


@app.get("/cycles")
def cycles(min_amount: float = 5000, window_hours: int = 72, limit: int = 200):
    return detection.find_cycles(min_amount=min_amount, window_hours=window_hours, limit=limit)


@app.get("/mules")
def mules(min_senders: int = 10, window_hours: int = 72, out_ratio: float = 0.7):
    return detection.find_mules(min_senders, window_hours, out_ratio)


@app.get("/risk")
def risk(top: int = 50):
    return detection.risk_scores(top=top)


@app.get("/graph")
def graph(customers: list[str] = Query(default=[]), accounts: list[str] = Query(default=[])):
    return detection.subgraph(customers, accounts)
