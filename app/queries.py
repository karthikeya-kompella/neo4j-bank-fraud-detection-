"""All Cypher lives here so it is easy to read, review and tune."""

# --- Pattern 1: shared identity (device / address / phone) -------------------
# Any identifier used by 2..$max_share customers links those customers.
# $max_share protects against "public wifi" style identifiers that connect thousands.
SHARED_IDENTIFIERS = """
MATCH (c:Customer)-[:USES|HAS_ADDRESS|HAS_PHONE]->(x)
WITH x, collect(DISTINCT c.id) AS customers
WHERE size(customers) >= 2 AND size(customers) <= $max_share
RETURN labels(x)[0] AS kind, x.id AS value, customers
"""

# Money moved between accounts owned by ring members.
RING_INTERNAL_FLOW = """
MATCH (c1:Customer)-[:OWNS]->(:Account)-[t:TRANSFERRED]->(:Account)<-[:OWNS]-(c2:Customer)
WHERE c1.id IN $members AND c2.id IN $members AND c1 <> c2
RETURN count(t) AS transfers, coalesce(sum(t.amount), 0.0) AS total
"""

# --- Pattern 2: circular money flow (layering / round-tripping) --------------
# A -> B -> C -> A with big amounts, time-ordered, inside a short window.
# The all(...) over relationships(p) is placed right after MATCH so the planner can
# prune during expansion instead of expanding every path first.
CYCLES = """
MATCH p = (a:Account)-[:TRANSFERRED*3..5]->(a)
WHERE all(r IN relationships(p) WHERE r.amount >= $min_amount)
WITH relationships(p) AS rs, [n IN nodes(p)[0..-1] | n.id] AS ids
WHERE all(i IN range(1, size(ids) - 1) WHERE NOT ids[i] IN ids[0..i])
  AND all(i IN range(0, size(rs) - 2) WHERE rs[i].ts <= rs[i + 1].ts)
  AND rs[-1].ts - rs[0].ts <= $window_s
RETURN ids AS accounts,
       [r IN rs | r.amount] AS amounts,
       reduce(s = 0.0, r IN rs | s + r.amount) AS total,
       rs[-1].ts - rs[0].ts AS span_s
ORDER BY total DESC
LIMIT $limit
"""

# --- Pattern 3: mule accounts (fan-in then quick fan-out) ---------------------
MULES = """
MATCH (a:Account)
CALL {
  WITH a
  MATCH (a)<-[i:TRANSFERRED]-(s:Account)
  RETURN count(DISTINCT s) AS senders,
         coalesce(sum(i.amount), 0.0) AS in_amount,
         min(i.ts) AS first_in, max(i.ts) AS last_in,
         collect(DISTINCT s.id)[..25] AS sender_ids
}
WITH a, senders, in_amount, first_in, last_in, sender_ids
WHERE senders >= $min_senders AND last_in - first_in <= $window_s
CALL {
  WITH a
  OPTIONAL MATCH (a)-[o:TRANSFERRED]->(r:Account)
  RETURN coalesce(sum(o.amount), 0.0) AS out_amount,
         [x IN collect(DISTINCT r.id) WHERE x IS NOT NULL] AS receiver_ids
}
WITH a, senders, in_amount, out_amount, sender_ids, receiver_ids
WHERE out_amount >= $out_ratio * in_amount
MATCH (c:Customer)-[:OWNS]->(a)
RETURN a.id AS account, c.id AS customer, c.name AS name,
       senders, in_amount, out_amount, sender_ids, receiver_ids
ORDER BY senders DESC
"""

# --- Lookups ------------------------------------------------------------------
ACCOUNT_OWNERS = """
MATCH (c:Customer)-[:OWNS]->(a:Account)
WHERE a.id IN $ids
RETURN a.id AS account, c.id AS customer
"""

CUSTOMER_NAMES = """
MATCH (c:Customer) WHERE c.id IN $ids
RETURN c.id AS id, c.name AS name
"""

STATS = """
MATCH (n) RETURN labels(n)[0] AS label, count(*) AS count
ORDER BY count DESC
"""

REL_STATS = """
MATCH ()-[r]->() RETURN type(r) AS type, count(*) AS count
ORDER BY count DESC
"""

# --- Subgraph for the visualiser ---------------------------------------------
SUB_OWNERS = """
MATCH (c:Customer)-[:OWNS]->(a:Account)
WHERE c.id IN $customers OR a.id IN $accounts
RETURN c.id AS cid, c.name AS cname, a.id AS aid
"""

SUB_IDENTIFIERS = """
MATCH (c:Customer)-[r:USES|HAS_ADDRESS|HAS_PHONE]->(x)
WHERE c.id IN $cids
RETURN c.id AS cid, type(r) AS rel, labels(x)[0] AS kind, x.id AS xid
"""

SUB_TRANSFERS = """
MATCH (a:Account)-[t:TRANSFERRED]->(b:Account)
WHERE a.id IN $aids AND b.id IN $aids
RETURN a.id AS src, b.id AS dst, t.amount AS amount, t.ts AS ts
"""
