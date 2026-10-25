"""Generate a synthetic banking dataset with PLANTED fraud so detection can be measured.

Run from the project root:
    python -m scripts.generate_data --customers 2000 --seed 42
Outputs CSVs + ground_truth.json into ./data
"""
import argparse
import csv
import json
import math
import random
import time
from pathlib import Path

FIRST = ["Aarav", "Vivaan", "Aditya", "Sai", "Arjun", "Krishna", "Ishaan", "Rohan", "Karthik",
         "Ananya", "Diya", "Meera", "Priya", "Sneha", "Kavya", "Riya", "Lakshmi", "Pooja",
         "Rahul", "Vikram", "Suresh", "Ramesh", "Anjali", "Divya", "Harsha", "Naveen"]
LAST = ["Reddy", "Sharma", "Patel", "Kumar", "Naidu", "Rao", "Singh", "Gupta", "Iyer",
        "Nair", "Verma", "Das", "Chowdary", "Varma", "Menon", "Joshi", "Mishra", "Yadav"]

NOW = int(time.time())
DAY = 86400


def pad(prefix: str, n: int, width: int) -> str:
    return f"{prefix}{n:0{width}d}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--customers", type=int, default=2000)
    ap.add_argument("--rings", type=int, default=6)
    ap.add_argument("--mules", type=int, default=3)
    ap.add_argument("--transfers", type=int, default=8000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default="data")
    args = ap.parse_args()

    rnd = random.Random(args.seed)
    out = Path(args.out)
    out.mkdir(exist_ok=True)

    customers, accounts, identifiers, transfers = [], [], [], []
    owner_accounts: dict[str, list[str]] = {}
    acc_n = 0

    # --- legit customers + accounts + (unique) identities ---------------------
    for i in range(1, args.customers + 1):
        cid = pad("C", i, 5)
        name = f"{rnd.choice(FIRST)} {rnd.choice(LAST)}"
        customers.append({"id": cid, "name": name, "signup_ts": NOW - rnd.randint(30, 900) * DAY})
        owner_accounts[cid] = []
        for _ in range(2 if rnd.random() < 0.25 else 1):
            acc_n += 1
            aid = pad("A", acc_n, 5)
            owner_accounts[cid].append(aid)
            accounts.append({"id": aid, "customer_id": cid, "opened_ts": NOW - rnd.randint(10, 800) * DAY})
        identifiers.append({"customer_id": cid, "kind": "Device", "value": f"DEV-L{i:05d}"})
        identifiers.append({"customer_id": cid, "kind": "Phone", "value": f"+91-9{rnd.randint(10**8, 10**9 - 1)}"})
        identifiers.append({"customer_id": cid, "kind": "Address", "value": f"ADDR-L{i:05d}"})

    ids = [c["id"] for c in customers]
    rnd.shuffle(ids)
    pool = iter(ids)

    # --- harmless noise: families sharing one address (pairs only) ------------
    family_pairs = int(args.customers * 0.04)
    for k in range(family_pairs):
        a, b = next(pool), next(pool)
        shared = f"ADDR-F{k:04d}"
        for cid in (a, b):
            for row in identifiers:
                if row["customer_id"] == cid and row["kind"] == "Address":
                    row["value"] = shared

    # --- PLANTED fraud rings --------------------------------------------------
    truth = {"rings": [], "cycles": [], "mules": []}
    for r in range(args.rings):
        size = rnd.randint(4, 7)
        members = [next(pool) for _ in range(size)]
        truth["rings"].append(sorted(members))
        dev = [f"DEV-R{r}-{k}" for k in range(2)]
        phone = f"+91-98{r:02d}{rnd.randint(10**5, 10**6 - 1)}"
        for idx, cid in enumerate(members):
            identifiers[:] = [
                x for x in identifiers
                if not (x["customer_id"] == cid and x["kind"] in ("Device", "Phone"))
            ]
            if idx == 0:  # bridges both devices so the ring is one connected component
                identifiers += [{"customer_id": cid, "kind": "Device", "value": d} for d in dev]
            else:
                identifiers.append({"customer_id": cid, "kind": "Device", "value": dev[idx % 2]})
            if idx % 2 == 0:
                identifiers.append({"customer_id": cid, "kind": "Phone", "value": phone})
            else:
                identifiers.append({"customer_id": cid, "kind": "Phone", "value": f"+91-9{rnd.randint(10**8, 10**9 - 1)}"})

        # circular laundering between the ring's accounts
        ring_accounts = [owner_accounts[c][0] for c in members]
        for _ in range(2):
            hops = rnd.randint(3, min(4, len(ring_accounts)))
            loop = rnd.sample(ring_accounts, hops)
            amount = rnd.randint(9000, 48000)
            ts = NOW - rnd.randint(2, 25) * DAY
            for h in range(hops):
                src, dst = loop[h], loop[(h + 1) % hops]
                transfers.append({"src": src, "dst": dst, "amount": round(amount, 2), "ts": ts})
                amount *= rnd.uniform(0.96, 0.99)  # small "fee" skimmed each hop
                ts += rnd.randint(2, 8) * 3600
            truth["cycles"].append(sorted(loop))

    # --- PLANTED mule accounts ------------------------------------------------
    all_acc = [a["id"] for a in accounts]
    for _ in range(args.mules):
        mule_owner = next(pool)
        mule = owner_accounts[mule_owner][0]
        senders = rnd.sample([a for a in all_acc if a != mule], rnd.randint(14, 20))
        start = NOW - rnd.randint(3, 40) * DAY
        total = 0.0
        last = start
        for s in senders:
            amt = round(rnd.uniform(150, 900), 2)
            last = start + rnd.randint(0, 48 * 3600)
            total += amt
            transfers.append({"src": s, "dst": mule, "amount": amt, "ts": last})
        for dest in rnd.sample([a for a in all_acc if a != mule and a not in senders], 2):
            transfers.append({
                "src": mule, "dst": dest,
                "amount": round(total * 0.46, 2),
                "ts": start + 49 * 3600 + rnd.randint(0, 12 * 3600),
            })
        truth["mules"].append(mule)

    # --- ordinary background transfers ---------------------------------------
    for _ in range(args.transfers):
        src, dst = rnd.sample(all_acc, 2)
        amt = round(math.exp(rnd.gauss(6.2, 1.0)), 2)  # median ~ 490, rare big ones
        transfers.append({"src": src, "dst": dst, "amount": amt, "ts": NOW - rnd.randint(0, 90 * DAY)})

    for i, t in enumerate(transfers, 1):
        t["id"] = pad("T", i, 7)

    def dump(name, rows, fields):
        with open(out / name, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)

    dump("customers.csv", customers, ["id", "name", "signup_ts"])
    dump("accounts.csv", accounts, ["id", "customer_id", "opened_ts"])
    dump("identifiers.csv", identifiers, ["customer_id", "kind", "value"])
    dump("transfers.csv", transfers, ["id", "src", "dst", "amount", "ts"])
    (out / "ground_truth.json").write_text(json.dumps(truth, indent=2))

    print(f"customers={len(customers)} accounts={len(accounts)} identifiers={len(identifiers)} "
          f"transfers={len(transfers)}")
    print(f"planted: {len(truth['rings'])} rings, {len(truth['cycles'])} cycles, {len(truth['mules'])} mules")


if __name__ == "__main__":
    main()
