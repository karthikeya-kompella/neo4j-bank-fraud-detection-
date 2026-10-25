"""Compare what the graph queries detect against the PLANTED fraud in data/ground_truth.json.

Run from the project root (after loading the graph):
    python -m scripts.evaluate
"""
import json
from pathlib import Path

from app import detection
from app.db import close_driver


def prf(tp: int, detected: int, planted: int) -> tuple[float, float, float]:
    precision = tp / detected if detected else 0.0
    recall = tp / planted if planted else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return precision, recall, f1


def report(name: str, tp: int, detected: int, planted: int):
    p, r, f = prf(tp, detected, planted)
    print(f"{name:<8} planted={planted:<3} detected={detected:<3} correct={tp:<3} "
          f"precision={p:.2f} recall={r:.2f} f1={f:.2f}")


def main():
    truth = json.loads(Path("data/ground_truth.json").read_text())

    # Rings: a detected ring is correct if it matches a planted ring exactly.
    planted_rings = {frozenset(r) for r in truth["rings"]}
    found_rings = {frozenset(r["customers"]) for r in detection.find_rings()}
    report("rings", len(planted_rings & found_rings), len(found_rings), len(planted_rings))

    # Cycles: compare as sets of accounts.
    planted_cycles = {frozenset(c) for c in truth["cycles"]}
    found_cycles = {frozenset(c["accounts"]) for c in detection.find_cycles()}
    report("cycles", len(planted_cycles & found_cycles), len(found_cycles), len(planted_cycles))

    # Mules: compare account ids.
    planted_mules = set(truth["mules"])
    found_mules = {m["account"] for m in detection.find_mules()}
    report("mules", len(planted_mules & found_mules), len(found_mules), len(planted_mules))

    close_driver()


if __name__ == "__main__":
    main()
