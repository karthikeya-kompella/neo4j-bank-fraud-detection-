"""Fraud detection logic: runs the Cypher patterns and post-processes results in Python."""
from collections import defaultdict

from app import queries as q
from app.db import run_read


class DisjointSet:
    """Union-Find (DSU): groups items that are connected, in near-O(1) per operation."""

    def __init__(self):
        self.parent: dict[str, str] = {}

    def find(self, x: str) -> str:
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]  # path compression
            x = self.parent[x]
        return x

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


def find_rings(min_size: int = 3, max_share: int = 12) -> list[dict]:
    """Customers linked (directly or transitively) by shared device/address/phone."""
    rows = run_read(q.SHARED_IDENTIFIERS, max_share=max_share)

    dsu = DisjointSet()
    for row in rows:
        first, *rest = row["customers"]
        dsu.find(first)
        for other in rest:
            dsu.union(first, other)

    members: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        for cid in row["customers"]:
            members[dsu.find(cid)].add(cid)

    shared: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        shared[dsu.find(row["customers"][0])].append(
            {"kind": row["kind"], "value": row["value"], "customers": len(row["customers"])}
        )

    rings = []
    for root, ids in members.items():
        if len(ids) < min_size:
            continue
        ids_sorted = sorted(ids)
        flow = run_read(q.RING_INTERNAL_FLOW, members=ids_sorted)[0]
        rings.append(
            {
                "ring_id": f"RING-{ids_sorted[0]}",
                "size": len(ids_sorted),
                "customers": ids_sorted,
                "shared_identifiers": sorted(shared[root], key=lambda s: (s["kind"], s["value"])),
                "internal_transfers": flow["transfers"],
                "internal_volume": round(flow["total"], 2),
            }
        )
    rings.sort(key=lambda r: (r["size"], r["internal_volume"]), reverse=True)
    return rings


def find_cycles(min_amount: float = 5000, window_hours: int = 72, limit: int = 200) -> list[dict]:
    rows = run_read(
        q.CYCLES, min_amount=min_amount, window_s=window_hours * 3600, limit=limit
    )
    seen: set[frozenset] = set()
    out = []
    for row in rows:
        key = frozenset(row["accounts"])
        if key in seen:  # the same loop can be found from different start points
            continue
        seen.add(key)
        out.append(
            {
                "accounts": row["accounts"],
                "hops": len(row["accounts"]),
                "amounts": [round(a, 2) for a in row["amounts"]],
                "total": round(row["total"], 2),
                "span_hours": round(row["span_s"] / 3600, 1),
            }
        )
    return out


def find_mules(min_senders: int = 10, window_hours: int = 72, out_ratio: float = 0.7) -> list[dict]:
    rows = run_read(
        q.MULES, min_senders=min_senders, window_s=window_hours * 3600, out_ratio=out_ratio
    )
    for r in rows:
        r["in_amount"] = round(r["in_amount"], 2)
        r["out_amount"] = round(r["out_amount"], 2)
    return rows


def risk_scores(top: int = 50) -> list[dict]:
    """Combine the three signals into one explainable 0-100 score per customer."""
    rings = find_rings()
    cycles = find_cycles()
    mules = find_mules()

    score: dict[str, int] = defaultdict(int)
    reasons: dict[str, list[str]] = defaultdict(list)

    for ring in rings:
        for cid in ring["customers"]:
            score[cid] += 25 + 2 * min(ring["size"], 10)
            reasons[cid].append(f"member of {ring['ring_id']} (size {ring['size']})")

    cycle_accounts = sorted({a for c in cycles for a in c["accounts"]})
    if cycle_accounts:
        for row in run_read(q.ACCOUNT_OWNERS, ids=cycle_accounts):
            score[row["customer"]] += 35
            reasons[row["customer"]].append(f"account {row['account']} sits in a circular transfer")

    for m in mules:
        score[m["customer"]] += 30
        reasons[m["customer"]].append(
            f"account {m['account']} looks like a mule ({m['senders']} senders, fast pass-through)"
        )

    ranked = sorted(score.items(), key=lambda kv: kv[1], reverse=True)[:top]
    names = {r["id"]: r["name"] for r in run_read(q.CUSTOMER_NAMES, ids=[c for c, _ in ranked])}
    return [
        {"customer": cid, "name": names.get(cid, ""), "score": min(s, 100), "reasons": reasons[cid]}
        for cid, s in ranked
    ]


def subgraph(customers: list[str], accounts: list[str]) -> dict:
    """Nodes + edges for the browser visualiser."""
    owners = run_read(q.SUB_OWNERS, customers=customers, accounts=accounts)
    cids = sorted({r["cid"] for r in owners})
    aids = sorted({r["aid"] for r in owners})

    nodes: dict[str, dict] = {}
    edges: list[dict] = []

    for r in owners:
        nodes[r["cid"]] = {"id": r["cid"], "label": r["cname"], "group": "Customer"}
        nodes[r["aid"]] = {"id": r["aid"], "label": r["aid"], "group": "Account"}
        edges.append({"from": r["cid"], "to": r["aid"], "label": "OWNS", "kind": "owns"})

    for r in run_read(q.SUB_IDENTIFIERS, cids=cids):
        nodes.setdefault(r["xid"], {"id": r["xid"], "label": r["xid"], "group": r["kind"]})
        edges.append({"from": r["cid"], "to": r["xid"], "label": r["rel"], "kind": "identity"})

    for r in run_read(q.SUB_TRANSFERS, aids=aids):
        edges.append(
            {
                "from": r["src"],
                "to": r["dst"],
                "label": f"{r['amount']:,.0f}",
                "kind": "transfer",
                "arrows": "to",
            }
        )

    return {"nodes": list(nodes.values()), "edges": edges}
